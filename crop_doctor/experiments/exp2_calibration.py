"""Experiment 2: is the confidence honest, and does temperature scaling fix it on field photos?

    python -m crop_doctor.experiments.exp2_calibration

Temperature T is fitted on different labelled photos, then judged on field_test (never used for fitting):
  raw          T = 1 (no fix)
  T_lab        fitted on lab_val (the usual recipe: only lab data available)
  T_field_N    fitted on N expert-labelled field photos drawn from field_pool (N = 25, 50, 100), 20 random draws
  T_field_all  fitted on the whole field_pool (475 photos)

Figure 2: reliability diagrams (confidence vs actual accuracy).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from crop_doctor import config
from crop_doctor.experiments.common import FIELD, FIXED, INK_2, LAB, load, save_fig, save_metrics, style
from crop_doctor.uncertainty.calibration import fit_temperature, reliability_bins, softmax, summary

BUDGETS = (25, 50, 100)
DRAWS = 20
MIN_BIN = 5  # bins with fewer photos are not drawn (they still count in ECE)


def reliability_panel(ax, probs, labels, color, title, stats):
    b = reliability_bins(probs, labels, n_bins=10)
    centers = (b["edges"][:-1] + b["edges"][1:]) / 2
    used = b["count"] >= MIN_BIN  # a bar from 1-4 photos is noise, not evidence
    ax.plot([0, 1], [0, 1], color=INK_2, lw=1, ls="--", label="perfectly honest")
    ax.bar(centers[used], b["accuracy"][used], width=0.09, color=color, alpha=0.9, label="actual accuracy")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Model's confidence")
    ax.set_ylabel("Actual accuracy")
    ax.set_title(title, fontsize=10)
    ax.text(0.03, 0.97, f"ECE {stats['ece']:.2f}\nconfidence {stats['mean_confidence']:.0%}\naccuracy {stats['accuracy']:.0%}",
            transform=ax.transAxes, va="top", fontsize=8.5, color=INK_2,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="none", alpha=0.85))


def main() -> None:
    style()
    lab_val_logits, lab_val_y, _ = load("lab_val")
    lab_test_logits, lab_test_y, _ = load("lab_test")
    pool_logits, pool_y, _ = load("field_pool")
    test_logits, test_y, _ = load("field_test")

    t_lab = fit_temperature(lab_val_logits, lab_val_y)
    t_field_all = fit_temperature(pool_logits, pool_y)

    res = {
        "temperatures": {"T_lab": round(t_lab, 3), "T_field_all": round(t_field_all, 3)},
        "lab_test": {"raw": summary(softmax(lab_test_logits), lab_test_y),
                     "T_lab": summary(softmax(lab_test_logits, t_lab), lab_test_y)},
        "field_test": {"raw": summary(softmax(test_logits), test_y),
                       "T_lab": summary(softmax(test_logits, t_lab), test_y),
                       "T_field_all": summary(softmax(test_logits, t_field_all), test_y)},
        "field_budget": {},
    }

    rng = np.random.default_rng(config.SEED)
    for n in BUDGETS:
        temps, eces = [], []
        for _ in range(DRAWS):
            idx = rng.choice(len(pool_y), size=n, replace=False)
            t = fit_temperature(pool_logits[idx], pool_y[idx])
            temps.append(t)
            eces.append(summary(softmax(test_logits, t), test_y)["ece"])
        res["field_budget"][f"N={n}"] = {"T_mean": round(float(np.mean(temps)), 3), "T_std": round(float(np.std(temps)), 3),
                                         "ece_mean": round(float(np.mean(eces)), 4), "ece_std": round(float(np.std(eces)), 4)}

    # Figure 2: four reliability diagrams.
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
    panels = [
        (softmax(lab_test_logits), lab_test_y, LAB, "Lab photos", res["lab_test"]["raw"]),
        (softmax(test_logits), test_y, FIELD, "Field photos (raw)", res["field_test"]["raw"]),
        (softmax(test_logits, t_lab), test_y, FIELD, f"Field, T from lab (T={t_lab:.2f})", res["field_test"]["T_lab"]),
        (softmax(test_logits, t_field_all), test_y, FIXED, f"Field, T from field (T={t_field_all:.2f})",
         res["field_test"]["T_field_all"]),
    ]
    for ax, (p, y, c, title, stats) in zip(axes, panels):
        reliability_panel(ax, p, y, c, title, stats)
    for ax in axes[1:]:
        ax.set_ylabel("")
    axes[3].legend(loc="lower right", fontsize=8)  # panel 4 has empty space on the right
    fig.suptitle("Is the model's confidence honest? Bars on the dashed line = honest; bars below it = overconfident "
                 f"(bins with < {MIN_BIN} photos not drawn)", fontsize=11, y=1.06)
    save_fig(fig, "fig2_reliability")

    save_metrics("exp2_calibration", res)
    print(f"  T_lab = {t_lab:.3f}   T_field_all = {t_field_all:.3f}")
    for name, s in res["field_test"].items():
        print(f"  field_test {name:<12} ECE {s['ece']:.3f}  NLL {s['nll']:.3f}  mean conf {s['mean_confidence']:.3f}  acc {s['accuracy']:.3f}")
    for n, s in res["field_budget"].items():
        print(f"  field_test T from {n:<6} ECE {s['ece_mean']:.3f} ± {s['ece_std']:.3f}  (T {s['T_mean']:.2f} ± {s['T_std']:.2f})")


if __name__ == "__main__":
    main()
