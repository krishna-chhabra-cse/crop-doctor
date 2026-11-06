"""Experiment 8: the v2 model (more field data, 11 classes) vs the v1 app model, on held-out field photos.

    python -m crop_doctor.experiments.exp8_final_v2

Test set (never used for training, model choice or calibration): splits_v2/field_test =
PlantDoc field_test (476 web photos, the same as before) + Tanzania test (~940 farm photos).
Everything is reported PER SOURCE, because one big average would hide a weak source.

Also: the "unknown disease" probe. Tomato-Village photos of diseases the app was never taught (leaf miner,
spotted wilt virus, nutrient deficiencies). An honest assistant should NOT confidently name one of its 11
diseases for these; we measure how often it asks/escalates instead.

Writes metrics/exp8_final_v2.json, figures/fig6_v2.png, and outputs/app_model.json (the app now uses v2).
"""
from __future__ import annotations

import json
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader

from crop_doctor import config
from crop_doctor.experiments.common import FIELD, FIXED, INK, save_fig, save_metrics, style
from crop_doctor.model.common import FrameDataset, device, eval_transform, load_trained_model
from crop_doctor.model.crops import crop_mask, crops_from_labels, mask_logits
from crop_doctor.model.train_final import logits_of
from crop_doctor.uncertainty.calibration import ece, fit_temperature, softmax
from crop_doctor.uncertainty.conformal import (
    aps_scores, class_coverage, conformal_quantile, evaluate_sets, prediction_sets, uniform_noise,
)

SPLITS = config.ROOT / "crop_doctor" / "data" / "splits_v2"
V2_CKPT, V1_CKPT = "final_v2_convnext_tiny.pt", "final_convnext_tiny.pt"
ALPHAS = (0.1, 0.2)


def raw_logits(ckpt: str, df: pd.DataFrame, dev) -> tuple[np.ndarray, list[str]]:
    model, classes = load_trained_model(dev, config.OUTPUTS_DIR / ckpt)
    dl = DataLoader(FrameDataset(df.assign(label_idx=0), eval_transform()), batch_size=64, num_workers=4)
    return logits_of(model, dl, dev), classes


def to_v2_columns(logits: np.ndarray, from_classes: list[str], to_classes: list[str]) -> np.ndarray:
    """v1 has no potato_healthy: give it -inf (it can never predict a class it doesn't know)."""
    out = np.full((len(logits), len(to_classes)), -np.inf)
    for j, c in enumerate(from_classes):
        out[:, to_classes.index(c)] = logits[:, j]
    return out


def main() -> None:
    style()
    dev = device()
    classes = json.loads((SPLITS / "classes.json").read_text())
    cal, test = pd.read_csv(SPLITS / "field_cal.csv"), pd.read_csv(SPLITS / "field_test.csv")
    probe = pd.read_csv(SPLITS / "unknown_probe.csv")
    cal_y, test_y = cal["label_idx"].to_numpy(), test["label_idx"].to_numpy()
    src = test["source"].to_numpy()

    lg2_cal, _ = raw_logits(V2_CKPT, cal, dev)
    lg2_test, _ = raw_logits(V2_CKPT, test, dev)
    lg1_test, v1_classes = raw_logits(V1_CKPT, test, dev)
    lg2_cal = mask_logits(lg2_cal, classes, crops_from_labels(cal_y, classes))
    crops = crops_from_labels(test_y, classes)
    lg2_test = mask_logits(lg2_test, classes, crops)
    lg1_test = mask_logits(to_v2_columns(lg1_test, v1_classes, classes), classes, crops)

    t = fit_temperature(lg2_cal, cal_y)
    qhat = {a: conformal_quantile(aps_scores(softmax(lg2_cal, t), cal_y, uniform_noise(len(cal_y), 7)), a) for a in ALPHAS}
    probs = softmax(lg2_test, t)
    u = uniform_noise(len(test_y), 12345)

    res = {"temperature": t, "qhat": {str(a): q for a, q in qhat.items()}, "test_photos": int(len(test_y)),
           "calibration_photos": int(len(cal_y)), "by_source": {}}
    for name, mask in [("all", np.ones(len(test_y), bool))] + [(s, src == s) for s in sorted(set(src))]:
        y, p2, p1 = test_y[mask], lg2_test[mask].argmax(1), lg1_test[mask].argmax(1)
        r = {"photos": int(mask.sum()),
             "v1_accuracy": float((p1 == y).mean()), "v2_accuracy": float((p2 == y).mean()),
             "v1_macro_f1": float(f1_score(y, p1, average="macro")), "v2_macro_f1": float(f1_score(y, p2, average="macro")),
             "v2_ece": ece(probs[mask], y)}
        for a in ALPHAS:
            sets = prediction_sets(probs[mask], qhat[a], u[mask])
            r[f"alpha_{a}"] = evaluate_sets(sets, y)
        res["by_source"][name] = r
        print(f"  {name:<9} n={r['photos']:<5} accuracy v1 {r['v1_accuracy']:.3f} -> v2 {r['v2_accuracy']:.3f} | "
              f"macro-F1 {r['v1_macro_f1']:.3f} -> {r['v2_macro_f1']:.3f} | coverage@90 {r['alpha_0.1']['coverage']:.3f} "
              f"set {r['alpha_0.1']['avg_set_size']:.2f} answered {r['alpha_0.1']['answered_rate']:.3f} "
              f"(acc {r['alpha_0.1']['answered_accuracy']:.3f})")
    cc = class_coverage(prediction_sets(probs, qhat[0.1], u), test_y, len(classes))
    res["class_coverage_90"] = {c: (None if np.isnan(v) else round(float(v), 3)) for c, v in zip(classes, cc)}

    # Unknown-disease probe (tomato): never-taught diseases.
    lgp, _ = raw_logits(V2_CKPT, probe, dev)
    lgp = lgp.copy()
    lgp[:, ~crop_mask(classes, "tomato")] = -np.inf
    pp = softmax(lgp, t)
    sets = prediction_sets(pp, qhat[0.1], uniform_noise(len(pp), 99))
    size = sets.sum(1)
    res["unknown_probe"] = {"photos": int(len(pp)), "named_one_disease": float((size == 1).mean()),
                            "asked_question_2_3": float(((size >= 2) & (size <= 3)).mean()),
                            "sent_to_expert_empty_or_long": float(((size == 0) | (size > 3)).mean()),
                            "by_disease": {d: float((size[probe["disease"].to_numpy() == d] == 1).mean())
                                           for d in sorted(probe["disease"].unique())}}
    up = res["unknown_probe"]
    print(f"  unknown diseases: named one disease {up['named_one_disease']:.1%}, asked a question "
          f"{up['asked_question_2_3']:.1%}, sent to expert {up['sent_to_expert_empty_or_long']:.1%}")
    save_metrics("exp8_final_v2", res)

    # Figure: accuracy per source, v1 vs v2, and coverage per source.
    names = [n for n in res["by_source"] if n != "all"] + ["all"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    x = np.arange(len(names))
    for off, key, color, label in ((-0.2, "v1_accuracy", FIELD, "v1 app model"), (0.2, "v2_accuracy", FIXED, "v2 (more field data)")):
        vals = [res["by_source"][n][key] for n in names]
        bars = a1.bar(x + off, vals, 0.37, color=color, label=label)
        for b, v in zip(bars, vals):
            a1.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.0%}", ha="center", fontsize=8.5, color=INK)
    a1.set_xticks(x, [n.capitalize() if n != "all" else "All test photos" for n in names])
    a1.set_ylim(0, 1.1)
    a1.set_title("Top answer correct on unseen field photos")
    a1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.08), ncol=2, fontsize=8.5)
    a1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    a1.grid(axis="x", visible=False)
    cov = [res["by_source"][n]["alpha_0.1"]["coverage"] for n in names]
    bars = a2.bar(x, cov, 0.5, color=FIXED)
    for b, v, n in zip(bars, cov, names):
        a2.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.0%} ({res['by_source'][n]['alpha_0.1']['avg_set_size']:.1f})",
                ha="center", fontsize=8.5, color=INK)
    a2.axhline(0.9, color="#52514e", lw=1, ls="--")
    a2.set_xticks(x, [n.capitalize() if n != "all" else "All test photos" for n in names])
    a2.set_ylim(0, 1.1)
    a2.set_title("v2 shortlist contains the true disease (avg. length)")
    a2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    a2.grid(axis="x", visible=False)
    save_fig(fig, "fig6_v2")

    # The app now uses v2.
    app = config.OUTPUTS_DIR / "app_model.json"
    if app.exists() and not (config.OUTPUTS_DIR / "app_model_v1.json").exists():
        shutil.copy(app, config.OUTPUTS_DIR / "app_model_v1.json")
    app.write_text(json.dumps({
        "checkpoint": V2_CKPT, "classes": classes, "temperature": t, "qhat": {str(a): q for a, q in qhat.items()},
        "default_alpha": 0.1, "calibrated_on": "splits_v2/field_cal",
        "splits": {"dir": "crop_doctor/data/splits_v2", "lab": "lab_val", "cal": "field_cal", "simulate": "field_val",
                   "monitor": "field_test"}}, indent=2))
    print("  outputs/app_model.json now points to the v2 model")


if __name__ == "__main__":
    main()
