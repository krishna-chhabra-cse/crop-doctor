"""Experiment 1: how much worse is the lab-trained model on real farm photos?

    python -m crop_doctor.experiments.exp1_shift

Figure 1a: accuracy and macro-F1, lab vs field.
Figure 1b: confusion matrix on field photos (which diseases get mixed up).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, recall_score

from crop_doctor.experiments.common import FIELD, INK, INK_2, LAB, load, pretty, save_fig, save_metrics, style
from crop_doctor.uncertainty.calibration import softmax


def main() -> None:
    style()
    results, per_class = {}, {}
    for split in ("lab_test", "field_test"):
        logits, y, classes = load(split)
        pred = logits.argmax(1)
        conf = softmax(logits).max(1)
        results[split] = {
            "images": int(len(y)),
            "accuracy": round(float((pred == y).mean()), 4),
            "macro_f1": round(float(f1_score(y, pred, average="macro")), 4),
            "mean_confidence": round(float(conf.mean()), 4),
            "mean_confidence_when_wrong": round(float(conf[pred != y].mean()), 4),
            "wrong_with_confidence_over_90": int(((pred != y) & (conf > 0.9)).sum()),
            "wrong_total": int((pred != y).sum()),
        }
        recalls = recall_score(y, pred, average=None, labels=range(len(classes)), zero_division=0)
        per_class[split] = {c: round(float(r), 3) for c, r in zip(classes, recalls)}

    # Figure 1a: grouped bars.
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    metrics = ["accuracy", "macro_f1"]
    x = np.arange(len(metrics))
    w = 0.36
    for off, split, color, name in ((-w / 2, "lab_test", LAB, "Lab photos (PlantVillage)"),
                                    (w / 2, "field_test", FIELD, "Field photos (PlantDoc)")):
        vals = [results[split][m] for m in metrics]
        bars = ax.bar(x + off, vals, w - 0.03, color=color, label=name)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.0%}", ha="center", color=INK, fontsize=9)
    ax.axhline(0.1, color=INK_2, lw=1, ls="--", label="Random guess (10%)")
    ax.set_xticks(x, ["Accuracy", "Macro-F1"])
    ax.set_xlim(-0.65, 1.65)
    ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("Same model, lab vs real farm photos", pad=28)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=7.5)
    ax.grid(axis="x", visible=False)
    save_fig(fig, "fig1a_lab_vs_field")

    # Figure 1b: row-normalised confusion matrix on field photos.
    logits, y, classes = load("field_test")
    cm = confusion_matrix(y, logits.argmax(1), labels=range(len(classes)), normalize="true")
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=1)
    names = [pretty(c) for c in classes]
    ax.set_xticks(range(len(classes)), names, rotation=45, ha="right")
    ax.set_yticks(range(len(classes)), names)
    ax.set_xlabel("Model's prediction")
    ax.set_ylabel("True disease")
    ax.grid(False)
    for i in range(len(classes)):
        for j in range(len(classes)):
            if cm[i, j] >= 0.1:
                ax.text(j, i, f"{cm[i, j]:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if cm[i, j] > 0.55 else INK)
    ax.set_title("Field photos: where the predictions go (each row sums to 100%)")
    fig.colorbar(im, ax=ax, fraction=0.04, format=plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    save_fig(fig, "fig1b_field_confusion")

    # Most common mistakes (true -> predicted), useful for the follow-up questions in the app.
    counts = confusion_matrix(y, logits.argmax(1), labels=range(len(classes)))
    np.fill_diagonal(counts, 0)
    top = np.dstack(np.unravel_index(np.argsort(-counts, axis=None)[:6], counts.shape))[0]
    mistakes = [{"true": classes[i], "predicted": classes[j], "count": int(counts[i, j])} for i, j in top]

    save_metrics("exp1_shift", {"results": results, "recall_per_class": per_class, "top_field_mistakes": mistakes})
    for split, r in results.items():
        print(f"  {split:<11} acc {r['accuracy']:.3f}  macro-F1 {r['macro_f1']:.3f}  mean conf {r['mean_confidence']:.3f}")
    print("  top field mistakes:", ", ".join(f"{m['true']}->{m['predicted']} ({m['count']})" for m in mistakes[:4]))


if __name__ == "__main__":
    main()
