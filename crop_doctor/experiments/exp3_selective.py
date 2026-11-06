"""Experiment 3: "answer only when sure". Does abstaining on low-confidence photos remove the mistakes?

    python -m crop_doctor.experiments.exp3_selective

Figure 3: risk-coverage curves (error rate among the answered photos vs share of photos answered).
Also: a threshold chosen on LAB photos to keep errors at <= 2%: what happens to it on FIELD photos?
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from crop_doctor.experiments.common import FIELD, INK_2, LAB, load, save_fig, save_metrics, style
from crop_doctor.uncertainty.calibration import softmax
from crop_doctor.uncertainty.selective import (
    apply_threshold, aurc, oracle_aurc, risk_at_coverage, risk_coverage, threshold_for_risk,
)

TARGET_RISK = 0.02


def scores(split: str):
    logits, y, _ = load(split)
    conf = softmax(logits).max(1)  # "max softmax probability": the simplest confidence signal
    return conf, logits.argmax(1) == y


def main() -> None:
    style()
    res = {}
    curves = {}
    for split in ("lab_test", "field_test"):
        conf, correct = scores(split)
        curves[split] = risk_coverage(conf, correct)
        res[split] = {
            "accuracy": round(float(correct.mean()), 4),
            "aurc": round(aurc(conf, correct), 4),
            "aurc_best_possible": round(oracle_aurc(correct), 4),
            "aurc_random_ranking": round(1 - float(correct.mean()), 4),
            **{f"error_when_answering_{int(c * 100)}pct": round(risk_at_coverage(conf, correct, c), 4)
               for c in (0.2, 0.5, 0.8, 1.0)},
        }

    # Threshold picked on lab_val, then reused unchanged: the "lab recipe".
    val_conf, val_correct = scores("lab_val")
    th = threshold_for_risk(val_conf, val_correct, TARGET_RISK)
    res["lab_threshold_transfer"] = {
        "target_error": TARGET_RISK,
        "lab_val": apply_threshold(val_conf, val_correct, th),
        "lab_test": apply_threshold(*scores("lab_test"), th),
        "field_test": apply_threshold(*scores("field_test"), th),
    }

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for split, color, name in (("lab_test", LAB, "Lab photos"), ("field_test", FIELD, "Field photos")):
        cov, risk = curves[split]
        ax.plot(cov, risk, color=color, label=f"{name} (AURC {res[split]['aurc']:.3f})")
    field_err = 1 - res["field_test"]["accuracy"]
    ax.axhline(field_err, color=FIELD, lw=1, ls=":")
    ax.text(0.98, field_err + 0.04, f"field error if it always answers ({field_err:.0%})", ha="right",
            color=INK_2, fontsize=8)
    ft = res["lab_threshold_transfer"]["field_test"]
    ax.plot([ft["coverage"]], [ft["risk"]], "o", ms=8, color=FIELD, markeredgecolor="white", markeredgewidth=2)
    ax.annotate(f"lab threshold (aims for {TARGET_RISK:.0%} error)\non field: answers {ft['coverage']:.0%}, "
                f"error {ft['risk']:.0%}", (ft["coverage"], ft["risk"]), xytext=(0.36, 0.42),
                textcoords="axes fraction", fontsize=8, color=INK_2, arrowprops=dict(arrowstyle="-", color=INK_2, lw=1))
    ax.set_xlabel("Share of photos the model answers (coverage)")
    ax.set_ylabel("Error rate among answered photos (risk)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fmt = plt.FuncFormatter(lambda v, _: f"{v:.0%}")
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)
    ax.set_title("Answer only when sure: does it remove the mistakes?")
    ax.legend(loc="center left", bbox_to_anchor=(0.02, 0.25), fontsize=8.5)
    save_fig(fig, "fig3_risk_coverage")

    save_metrics("exp3_selective", res)
    for split in ("lab_test", "field_test"):
        r = res[split]
        print(f"  {split:<11} AURC {r['aurc']:.3f} (best {r['aurc_best_possible']:.3f}, random {r['aurc_random_ranking']:.3f})"
              f"  error@20% {r['error_when_answering_20pct']:.3f}  error@50% {r['error_when_answering_50pct']:.3f}")
    t = res["lab_threshold_transfer"]
    print(f"  threshold {t['lab_val']['threshold']:.4f} from lab_val -> lab_test {t['lab_test']}  field_test {t['field_test']}")


if __name__ == "__main__":
    main()
