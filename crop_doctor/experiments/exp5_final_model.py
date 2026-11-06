"""Experiment 5: the final app model, evaluated once on the untouched field_test.

    python -m crop_doctor.experiments.exp5_final_model

1. Candidates (crop_doctor/outputs/final_*.pt) are compared on final_field_val; the best is chosen.
   field_test plays no part in this choice.
2. The chosen model and the Day 2 lab-only model (as a baseline) are both made crop-aware and calibrated
   (temperature + randomised APS) on the SAME final_field_cal photos, so the comparison is fair.
3. Both are evaluated on field_test at 90% and 80% target coverage.
4. The app's settings (checkpoint, temperature, q-hat) are saved to outputs/app_model.json.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader

from crop_doctor import config
from crop_doctor.experiments.common import FIELD, FIXED, INK, save_fig, save_metrics, style
from crop_doctor.model.common import CHECKPOINT, FrameDataset, device, eval_transform, load_classes, load_trained_model
from crop_doctor.model.crops import crop_of, crops_from_labels, mask_logits
from crop_doctor.model.train_final import final_splits, logits_of
from crop_doctor.uncertainty.calibration import ece, fit_temperature, nll, softmax
from crop_doctor.uncertainty.conformal import aps_scores, conformal_quantile, evaluate_sets, prediction_sets, uniform_noise

ALPHAS = (0.1, 0.2)
CAL_SEED, TEST_SEED = 7, 12345


def masked_logits(path, df, classes, dev) -> np.ndarray:
    model, _ = load_trained_model(dev, path)
    dl = DataLoader(FrameDataset(df, eval_transform()), batch_size=64, num_workers=4)
    y = df["label_idx"].to_numpy()
    return mask_logits(logits_of(model, dl, dev), classes, crops_from_labels(y, classes))


def evaluate(cal_logits, cal_y, test_logits, test_y, classes) -> dict:
    t = fit_temperature(cal_logits, cal_y)
    cal_p, test_p = softmax(cal_logits, t), softmax(test_logits, t)
    pred = test_p.argmax(1)
    out = {"temperature": t, "accuracy": float((pred == test_y).mean()),
           "macro_f1": float(f1_score(test_y, pred, average="macro")), "ece": ece(test_p, test_y),
           "per_crop_accuracy": {c: float((pred == test_y)[crops_from_labels(test_y, classes) == c].mean())
                                 for c in sorted({crop_of(x) for x in classes})}}
    for a in ALPHAS:
        q = conformal_quantile(aps_scores(cal_p, cal_y, uniform_noise(len(cal_y), CAL_SEED)), a)
        sets = prediction_sets(test_p, q, uniform_noise(len(test_y), TEST_SEED))
        out[f"alpha_{a}"] = {"qhat": q, **evaluate_sets(sets, test_y)}
    return out


def main() -> None:
    style()
    dev = device()
    classes = load_classes()
    sp = final_splits()
    val, cal = sp["final_field_val"], sp["final_field_cal"]
    test = pd.read_csv(config.SPLITS_DIR / "field_test.csv")
    val_y, cal_y, test_y = (d["label_idx"].to_numpy() for d in (val, cal, test))

    # 1. Choose the final model on field_val only.
    candidates = sorted(config.OUTPUTS_DIR.glob("final_*.pt"))
    candidates = [p for p in candidates if "smoke" not in p.name]
    selection = {}
    for p in candidates:
        vl = masked_logits(p, val, classes, dev)
        selection[p.name] = {"field_val_accuracy": float((vl.argmax(1) == val_y).mean()),
                             "field_val_nll": nll(softmax(vl), val_y)}
        print(f"  candidate {p.name:<28} val acc {selection[p.name]['field_val_accuracy']:.3f}  "
              f"NLL {selection[p.name]['field_val_nll']:.3f}")
    best = max(candidates, key=lambda p: (selection[p.name]["field_val_accuracy"], -selection[p.name]["field_val_nll"]))
    print(f"  chosen: {best.name}")

    # 2-3. Calibrate on field_cal, evaluate once on field_test.
    results = {}
    for name, path in (("baseline_lab_model", CHECKPOINT), ("final_model", best)):
        results[name] = evaluate(masked_logits(path, cal, classes, dev), cal_y,
                                 masked_logits(path, test, classes, dev), test_y, classes)
        r = results[name]
        print(f"  {name:<19} acc {r['accuracy']:.3f}  macro-F1 {r['macro_f1']:.3f}  ECE {r['ece']:.3f}  "
              f"per crop {', '.join(f'{k} {v:.2f}' for k, v in r['per_crop_accuracy'].items())}")
        for a in ALPHAS:
            s = r[f"alpha_{a}"]
            print(f"      target {1 - a:.0%}: coverage {s['coverage']:.3f}  set size {s['avg_set_size']:.2f}  "
                  f"answered alone {s['answered_rate']:.3f} (accuracy {s['answered_accuracy']:.3f})  empty {s['empty_rate']:.3f}")

    save_metrics("exp5_final_model", {"selection_on_field_val": selection, "chosen": best.name,
                                      "calibration_photos": len(cal_y), "test_photos": len(test_y), "results": results})
    f = results["final_model"]
    app = {"checkpoint": best.name, "classes": classes, "temperature": f["temperature"],
           "qhat": {str(a): f[f"alpha_{a}"]["qhat"] for a in ALPHAS}, "default_alpha": 0.1,
           "calibrated_on": "final_field_cal", "noise_note": "app uses fresh uniform noise per photo (randomised APS)"}
    (config.OUTPUTS_DIR / "app_model.json").write_text(json.dumps(app, indent=2))

    # Figure 5: baseline vs final, at 90% target.
    a = "alpha_0.1"
    metrics = [("Top-1\naccuracy", "accuracy", None), ("Coverage\n(target 90%)", "coverage", a),
               ("Answered alone\n(shortlist of 1)", "answered_rate", a),
               ("Correct when\nanswering alone", "answered_accuracy", a)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [3.2, 1]})
    x = np.arange(len(metrics))
    w = 0.38
    for off, key, color, label in ((-w / 2, "baseline_lab_model", FIELD, "Lab-only model (Day 2)"),
                                   (w / 2, "final_model", FIXED, f"Final model ({best.stem.replace('final_', '')})")):
        r = results[key]
        vals = [(r[k] if sub is None else r[sub][k]) for _, k, sub in metrics]
        vals = [0 if np.isnan(v) else v for v in vals]
        bars = ax1.bar(x + off, vals, w - 0.03, color=color, label=label)
        for b, v in zip(bars, vals):
            ax1.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.0%}", ha="center", fontsize=8.5, color=INK)
        s = r[a]["avg_set_size"]
        ax2.bar([off], [s], w - 0.03, color=color)
        ax2.text(off, s + 0.08, f"{s:.1f}", ha="center", fontsize=8.5, color=INK)
    ax1.set_xticks(x, [m[0] for m in metrics], fontsize=9)
    ax1.set_ylim(0, 1.1)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax1.grid(axis="x", visible=False)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=8.5)
    ax2.set_xticks([])
    ax2.set_title("Avg. shortlist size", fontsize=10)
    ax2.grid(axis="x", visible=False)
    fig.suptitle("Final crop-aware model vs lab-only model on unseen field photos (both calibrated on the same "
                 f"{len(cal_y)} field photos)", fontsize=11, fontweight="bold", y=1.04)
    save_fig(fig, "fig5_final_model")


if __name__ == "__main__":
    main()
