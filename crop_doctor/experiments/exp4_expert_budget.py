"""Experiment 4 (main result): how many expert-labelled field photos does it take to make the
assistant trustworthy on real farm photos, and is it better to only RECALIBRATE with them, or to
RETRAIN the model with them as well?

    python -m crop_doctor.experiments.exp4_expert_budget            # full run (~15-20 min on an RTX 3050)
    python -m crop_doctor.experiments.exp4_expert_budget --smoke    # 1-2 minute check
    python -m crop_doctor.experiments.exp4_expert_budget --plot-only

Simulation: field_pool plays the role of photos that experts label over time. For each budget N we
draw N of them at random (several random draws), then:

  A. Recalibrate only: fit temperature T and the conformal q-hat on the N labels. Model unchanged.
  B. Retrain + recalibrate: split the N labels in half. Retrain on one half (with lab replay),
     fit T and q-hat on the OTHER half (photos used for training can't be used for calibration:
     the model would be overconfident on them).
  N = 0 means "no field labels": T and q-hat come from lab_val (today's standard practice).

Everything is judged on field_test, which is never used for fitting. Target coverage: 90%.
Results are appended to metrics/exp4_runs.csv after every run, so an interrupted run can resume.
"""
from __future__ import annotations

import argparse
import json
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from crop_doctor import config
from crop_doctor.experiments.common import FIELD, FIXED, INK_2, METRICS_DIR, load, save_fig, style
from crop_doctor.model.common import device, load_trained_model
from crop_doctor.model.finetune import finetune, load_images, predict_logits, to_eval_tensor
from crop_doctor.uncertainty.calibration import ece, fit_temperature, softmax
from crop_doctor.uncertainty.conformal import (
    aps_scores, conformal_quantile, evaluate_sets, prediction_sets, uniform_noise,
)

ALPHA = 0.1                       # 90% target coverage
TEST_NOISE_SEED = 12345
BUDGETS = [0, 10, 25, 50, 100, 200, 475]
DRAWS = {"recalibrate": 20, "retrain": 5}
LAB_REPLAY_PER_CLASS = 200
RUNS_CSV = METRICS_DIR / "exp4_runs.csv"
COLUMNS = ["method", "N", "draw", "T", "qhat", "accuracy", "macro_f1", "ece", "coverage", "avg_set_size", "empty_rate",
           "answered_rate", "answered_accuracy", "train_photos", "cal_photos", "seconds"]
METHOD_LABEL = {"recalibrate": "A. Recalibrate only", "retrain": "B. Retrain + recalibrate"}


def score(cal_logits, cal_y, test_logits, test_y, seed: int) -> dict:
    """Fit T and q-hat on the calibration photos, evaluate everything on field_test."""
    t = fit_temperature(cal_logits, cal_y) if len(cal_y) else 1.0
    # Randomised APS with fixed seeds: calibration and test photos get their own reproducible "coin flips".
    qhat = conformal_quantile(aps_scores(softmax(cal_logits, t), cal_y, uniform_noise(len(cal_y), seed)), ALPHA)
    probs = softmax(test_logits, t)
    pred = probs.argmax(1)
    sets = prediction_sets(probs, qhat, uniform_noise(len(test_y), TEST_NOISE_SEED))
    return {"T": t, "qhat": qhat, "accuracy": float((pred == test_y).mean()),
            "macro_f1": float(f1_score(test_y, pred, average="macro")), "ece": ece(probs, test_y),
            **evaluate_sets(sets, test_y)}


def run(smoke: bool) -> None:
    budgets = [0, 10, 50] if smoke else BUDGETS
    draws = {"recalibrate": 2, "retrain": 1} if smoke else DRAWS
    steps = 20 if smoke else 150
    csv = METRICS_DIR / "exp4_runs_smoke.csv" if smoke else RUNS_CSV
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    done = set()
    if csv.exists():
        prev = pd.read_csv(csv)
        done = set(zip(prev["method"], prev["N"], prev["draw"]))

    def record(row):
        # Fixed column list so rows from both methods line up in one CSV.
        pd.DataFrame([row]).reindex(columns=COLUMNS).to_csv(csv, mode="a", header=not csv.exists(), index=False)
        print(f"  {row['method']:<11} N={row['N']:<4} draw {row['draw']}: coverage {row['coverage']:.3f} "
              f"set size {row['avg_set_size']:.2f} acc {row['accuracy']:.3f} answered {row['answered_rate']:.3f}", flush=True)

    lab_val_logits, lab_val_y, _ = load("lab_val")
    pool_logits, pool_y, _ = load("field_pool")
    test_logits, test_y, _ = load("field_test")

    # A. Recalibrate only: uses saved logits, so it's instant.
    for n in budgets:
        n_draws = 1 if n in (0, len(pool_y)) else draws["recalibrate"]
        for d in range(n_draws):
            if ("recalibrate", n, d) in done:
                continue
            if n == 0:
                r = score(lab_val_logits, lab_val_y, test_logits, test_y, seed=0)
            else:
                idx = np.random.default_rng(1000 * n + d).choice(len(pool_y), n, replace=False)
                r = score(pool_logits[idx], pool_y[idx], test_logits, test_y, seed=1000 * n + d)
            record({"method": "recalibrate", "N": n, "draw": d, **r})

    # B. Retrain + recalibrate: one short fine-tuning run per (N, draw).
    todo = [(n, d) for n in budgets if n > 0 for d in range(draws["retrain"]) if ("retrain", n, d) not in done]
    if not todo:
        return
    dev = device()
    base, _ = load_trained_model(dev)
    print("  loading images into memory ...", flush=True)
    pool_df = pd.read_csv(config.SPLITS_DIR / "field_pool.csv")
    test_df = pd.read_csv(config.SPLITS_DIR / "field_test.csv")
    lab_df = (pd.read_csv(config.SPLITS_DIR / "lab_train.csv").groupby("label", group_keys=False)
              .apply(lambda g: g.sample(min(len(g), LAB_REPLAY_PER_CLASS), random_state=config.SEED)))
    assert (pool_df["label_idx"].to_numpy() == pool_y).all() and (test_df["label_idx"].to_numpy() == test_y).all()
    pool_imgs = load_images(pool_df)
    pool_x = to_eval_tensor(pool_imgs)
    test_x = to_eval_tensor(load_images(test_df))
    lab_imgs, lab_y = load_images(lab_df), lab_df["label_idx"].to_numpy()

    for n, d in todo:
        t0 = time.time()
        rng = np.random.default_rng(1000 * n + d)
        idx = rng.choice(len(pool_y), n, replace=False)   # same photos as method A's draw d
        train_idx, cal_idx = idx[: n // 2], idx[n // 2:]
        model = finetune(base, [pool_imgs[i] for i in train_idx], pool_y[train_idx], lab_imgs, lab_y, dev,
                         steps=steps, seed=1000 * n + d)
        r = score(predict_logits(model, pool_x[cal_idx], dev), pool_y[cal_idx],
                  predict_logits(model, test_x, dev), test_y, seed=1000 * n + d)
        record({"method": "retrain", "N": n, "draw": d, **r, "train_photos": len(train_idx),
                "cal_photos": len(cal_idx), "seconds": round(time.time() - t0, 1)})
        del model


def summarise(csv=RUNS_CSV) -> pd.DataFrame:
    runs = pd.read_csv(csv)
    # N = 0 is the same starting point for both methods.
    zero = runs[(runs["method"] == "recalibrate") & (runs["N"] == 0)].assign(method="retrain")
    runs = pd.concat([runs, zero], ignore_index=True)
    cols = ["coverage", "avg_set_size", "empty_rate", "accuracy", "macro_f1", "ece", "answered_rate", "answered_accuracy"]
    agg = runs.groupby(["method", "N"])[cols].agg(["mean", "std"])
    agg.columns = [f"{c}_{s}" for c, s in agg.columns]
    return agg.reset_index().fillna({f"{c}_std": 0 for c in cols})


def plot(summary: pd.DataFrame) -> None:
    style()
    budgets = sorted(summary["N"].unique())
    xs = np.arange(len(budgets))
    xlabels = ["0\n(lab only)" if n == 0 else str(n) for n in budgets]
    panels = [
        ("coverage", "Does the shortlist contain the true disease?", "Coverage on field photos", True),
        ("avg_set_size", "How long is the shortlist? (shorter = more useful)", "Avg. diseases in shortlist", False),
        ("accuracy", "Is the top answer right?", "Top-1 accuracy on field photos", True),
        ("answered_rate", "How often can it answer alone? (shortlist of 1)", "Photos answered without expert", True),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6))
    for ax, (col, title, ylabel, pct) in zip(axes.flat, panels):
        for method, color in (("recalibrate", FIELD), ("retrain", FIXED)):
            s = summary[summary["method"] == method].set_index("N").reindex(budgets)
            m, sd = s[f"{col}_mean"].to_numpy(), s[f"{col}_std"].to_numpy()
            ax.plot(xs, m, "-o", color=color, ms=6, markeredgecolor="white", markeredgewidth=1.5,
                    label=METHOD_LABEL[method])
            ax.fill_between(xs, m - sd, m + sd, color=color, alpha=0.15, linewidth=0)
        if col == "coverage":
            ax.axhline(1 - ALPHA, color=INK_2, lw=1, ls="--")
            ax.text(xs[-1], 1 - ALPHA + 0.015, "90% target", ha="right", fontsize=8, color=INK_2)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel)
        ax.set_xticks(xs, xlabels)
        if pct:
            ax.set_ylim(0, 1.02)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        else:
            ax.set_ylim(0, None)
    for ax in axes[1]:
        ax.set_xlabel("Expert-labelled field photos available (N)")
    # Annotations that stop the two odd-looking points from being misread.
    zero = summary[(summary["method"] == "recalibrate") & (summary["N"] == 0)].iloc[0]
    axes[1, 1].annotate(f"lab-calibrated: answers {zero['answered_rate_mean']:.0%} alone,\n"
                        f"but only {zero['answered_accuracy_mean']:.0%} of those answers are right",
                        (0, zero["answered_rate_mean"]), xytext=(0.6, 0.8), fontsize=8, color=INK_2,
                        arrowprops=dict(arrowstyle="-", color=INK_2, lw=1))
    if 10 in budgets:
        i10 = budgets.index(10)
        axes[0, 1].annotate("B at N=10: only 5 photos left to calibrate,\ntoo few for a 90% guarantee -> all 10 diseases",
                            (i10, 10), xytext=(i10 + 0.6, 1.2), fontsize=8, color=INK_2,
                            arrowprops=dict(arrowstyle="-", color=INK_2, lw=1))
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0), fontsize=9)
    fig.suptitle("How many expert labels make the assistant trustworthy on real farm photos?",
                 fontsize=12, fontweight="bold", y=1.045)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    save_fig(fig, "fig4_expert_budget")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--plot-only", action="store_true")
    args = ap.parse_args()
    if not args.plot_only:
        run(args.smoke)
    if args.smoke:
        print(summarise(METRICS_DIR / "exp4_runs_smoke.csv").to_string())
        return
    summary = summarise()
    (METRICS_DIR / "exp4_summary.json").write_text(json.dumps(summary.round(4).to_dict(orient="records"), indent=2))
    plot(summary)
    show = ["method", "N", "coverage_mean", "avg_set_size_mean", "accuracy_mean", "answered_rate_mean",
            "answered_accuracy_mean", "ece_mean"]
    print(summary[show].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
