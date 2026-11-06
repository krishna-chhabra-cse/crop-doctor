"""Helpers shared by all experiment scripts: load saved logits, save metrics, consistent figure style."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")  # write image files, no window
import matplotlib.pyplot as plt
import numpy as np

from crop_doctor import config

FIG_DIR = config.OUTPUTS_DIR / "figures"
METRICS_DIR = config.OUTPUTS_DIR / "metrics"

# Same colour = same meaning in every figure.
LAB = "#2a78d6"      # blue: lab photos
FIELD = "#eb6834"    # orange: field photos (raw model)
FIXED = "#1baf7a"    # aqua: field photos after a fix (temperature / recalibration)
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"


def load(split: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    d = np.load(config.OUTPUTS_DIR / f"logits_{split}.npz", allow_pickle=True)
    return d["logits"].astype(np.float64), d["labels"].astype(int), [str(c) for c in d["classes"]]


def save_metrics(name: str, metrics: dict) -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    (METRICS_DIR / f"{name}.json").write_text(json.dumps(metrics, indent=2))


def style() -> None:
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.edgecolor": INK_2, "axes.labelcolor": INK, "xtick.color": INK_2, "ytick.color": INK_2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "legend.frameon": False, "lines.linewidth": 2,
    })


def save_fig(fig, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)
    print(f"  saved figures/{name}.png")


def pretty(label: str) -> str:
    return label.replace("tomato_", "Tomato ").replace("potato_", "Potato ").replace("_", " ")
