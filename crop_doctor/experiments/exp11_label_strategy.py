"""Experiment 11: if an expert can only label N field photos, should we show them the photos the
model is least sure about, or is a random choice just as good?

    python -m crop_doctor.experiments.exp11_label_strategy            # full run
    python -m crop_doctor.experiments.exp11_label_strategy --smoke    # quick check
    python -m crop_doctor.experiments.exp11_label_strategy --plot-only

Needs what Exp 4 needs: the trained lab model and the downloaded datasets.

Each draw:
  1. Set aside CAL_PHOTOS random field_pool photos for calibration, before any picking.
  2. From the rest, pick N photos for retraining, by "random" or "uncertain" (highest entropy under
     the lab model). Hard photos can therefore never enter calibration.
  3. Fine-tune with lab replay, fit T and q-hat on the calibration photos, judge on field_test.

Both strategies share each draw's calibration photos and training seed, so they can be compared
draw by draw. "none" (N = 0) is the unchanged lab model calibrated on the same photos.
Picking is one batch from the lab model, not repeated rounds.
"""
from __future__ import annotations

import argparse
import json
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from crop_doctor import config
from crop_doctor.experiments.common import FIELD, FIXED, INK_2, METRICS_DIR, save_fig, style
from crop_doctor.experiments.exp4_expert_budget import ALPHA, LAB_REPLAY_PER_CLASS, score
from crop_doctor.model.common import device, load_trained_model
from crop_doctor.model.finetune import finetune, load_images, predict_logits, to_eval_tensor
from crop_doctor.uncertainty.active import STRATEGIES, pick_for_labelling, split_pool
from crop_doctor.uncertainty.calibration import softmax

CAL_PHOTOS = 100
BUDGETS = [25, 50, 100, 200, 375]   # 375 = every photo left after calibration
DRAWS = 5
RUNS_CSV = METRICS_DIR / "exp11_runs.csv"
COLUMNS = ["strategy", "N", "draw", "T", "qhat", "accuracy", "macro_f1", "ece", "coverage", "avg_set_size",
           "empty_rate", "answered_rate", "answered_accuracy", "classes_picked", "seconds"]
METRICS = ["accuracy", "macro_f1", "ece", "coverage", "avg_set_size", "answered_rate", "answered_accuracy"]


def run(smoke: bool) -> None:
    budgets, draws, steps = ([25], 1, 20) if smoke else (BUDGETS, DRAWS, 150)
    csv = METRICS_DIR / "exp11_runs_smoke.csv" if smoke else RUNS_CSV
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    done = set()
    if csv.exists():
        prev = pd.read_csv(csv)
        done = set(zip(prev["strategy"], prev["N"], prev["draw"]))

    dev = device()
    base, _ = load_trained_model(dev)
    print("  loading images into memory ...", flush=True)
    pool_df = pd.read_csv(config.SPLITS_DIR / "field_pool.csv")
    test_df = pd.read_csv(config.SPLITS_DIR / "field_test.csv")
    lab_df = (pd.read_csv(config.SPLITS_DIR / "lab_train.csv").groupby("label", group_keys=False)
              .apply(lambda g: g.sample(min(len(g), LAB_REPLAY_PER_CLASS), random_state=config.SEED)))
    pool_y, test_y = pool_df["label_idx"].to_numpy(), test_df["label_idx"].to_numpy()
    pool_imgs = load_images(pool_df)
    pool_x, test_x = to_eval_tensor(pool_imgs), to_eval_tensor(load_images(test_df))
    lab_imgs, lab_y = load_images(lab_df), lab_df["label_idx"].to_numpy()
    base_logits = predict_logits(base, pool_x, dev)
    pool_probs = softmax(base_logits, 1.0)
    base_test_logits = predict_logits(base, test_x, dev)

    def record(row: dict) -> None:
        pd.DataFrame([row]).reindex(columns=COLUMNS).to_csv(csv, mode="a", header=not csv.exists(), index=False)
        print(f"  {row['strategy']:<9} N={row['N']:<4} draw {row['draw']}: coverage {row['coverage']:.3f} "
              f"set size {row['avg_set_size']:.2f} acc {row['accuracy']:.3f}", flush=True)

    for d in range(draws):
        seed = 7000 + d
        candidates, cal_idx = split_pool(len(pool_y), CAL_PHOTOS, seed)
        if ("none", 0, d) not in done:
            r = score(base_logits[cal_idx], pool_y[cal_idx], base_test_logits, test_y, seed=seed)
            record({"strategy": "none", "N": 0, "draw": d, **r})
        for n in budgets:
            for strategy in STRATEGIES:
                if (strategy, n, d) in done:
                    continue
                t0 = time.time()
                picked = pick_for_labelling(strategy, pool_probs, candidates, n, seed=seed + n)
                model = finetune(base, [pool_imgs[i] for i in picked], pool_y[picked], lab_imgs, lab_y, dev,
                                 steps=steps, seed=seed + n)
                r = score(predict_logits(model, pool_x[cal_idx], dev), pool_y[cal_idx],
                          predict_logits(model, test_x, dev), test_y, seed=seed)
                record({"strategy": strategy, "N": n, "draw": d, **r,
                        "classes_picked": len(set(pool_y[picked].tolist())),
                        "seconds": round(time.time() - t0, 1)})
                del model


def summarise(csv=RUNS_CSV) -> pd.DataFrame:
    runs = pd.read_csv(csv)
    agg = runs.groupby(["strategy", "N"])[METRICS].agg(["mean", "std"])
    agg.columns = [f"{c}_{s}" for c, s in agg.columns]
    return agg.reset_index()


def paired_difference(csv=RUNS_CSV) -> pd.DataFrame:
    """Uncertain minus random within the same draw, so calibration-photo luck cancels out."""
    runs = pd.read_csv(csv)
    keys = ["N", "draw"]
    rand = runs[runs["strategy"] == "random"].set_index(keys)
    unc = runs[runs["strategy"] == "uncertain"].set_index(keys)
    diff = (unc[METRICS] - rand[METRICS]).dropna(how="all").reset_index()
    out = diff.groupby("N")[METRICS].agg(["mean", "std"])
    out.columns = [f"{c}_{s}" for c, s in out.columns]
    return out.reset_index()


def plot(summary: pd.DataFrame) -> None:
    style()
    panels = [("accuracy", "Is the top answer right?"), ("coverage", "Is the true disease in the shortlist?"),
              ("avg_set_size", "Shortlist length (shorter is better)"), ("answered_rate", "Answered without an expert")]
    budgets = sorted(summary["N"].unique())
    xs = {n: i for i, n in enumerate(budgets)}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.4))
    zero = summary[summary["strategy"] == "none"]
    for ax, (col, title) in zip(axes.flat, panels):
        for strategy, color in (("random", FIELD), ("uncertain", FIXED)):
            s = pd.concat([zero, summary[summary["strategy"] == strategy]]).sort_values("N")
            x = [xs[n] for n in s["N"]]
            m, sd = s[f"{col}_mean"].to_numpy(), s[f"{col}_std"].fillna(0).to_numpy()
            ax.plot(x, m, "-o", color=color, label=strategy.capitalize())
            ax.fill_between(x, m - sd, m + sd, color=color, alpha=0.15, linewidth=0)
        if col == "coverage":
            ax.axhline(1 - ALPHA, color=INK_2, lw=1, ls="--")
        ax.set_title(title, fontsize=10)
        ax.set_xticks(list(xs.values()), budgets)
        ax.set_xlabel("Expert-labelled photos used for retraining")
    axes[0, 0].legend()
    fig.suptitle("Which photos should the expert label?", fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "fig11_label_strategy")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--plot-only", action="store_true")
    args = ap.parse_args()
    if not args.plot_only:
        run(args.smoke)
    csv = METRICS_DIR / "exp11_runs_smoke.csv" if args.smoke else RUNS_CSV
    summary, diff = summarise(csv), paired_difference(csv)
    print(summary.round(3).to_string(index=False))
    print("\nUncertain minus random, same draw:")
    print(diff.round(3).to_string(index=False))
    if args.smoke:
        return
    result = {"summary": summary.round(4).to_dict(orient="records"),
              "uncertain_minus_random": diff.round(4).to_dict(orient="records")}
    # pandas writes missing values as NaN, which is not valid JSON.
    (METRICS_DIR / "exp11_summary.json").write_text(json.dumps(json.loads(pd.Series([result]).to_json(orient="values"))[0], indent=2))
    plot(summary)


if __name__ == "__main__":
    main()
