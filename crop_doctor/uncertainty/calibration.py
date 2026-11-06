"""Is the model's confidence honest? Measure it (ECE) and fix it (temperature scaling).

Calibrated = "when the model says 80% sure, it is right 80% of the time".

All functions take plain NumPy arrays:
    logits: (n_images, n_classes) raw model outputs
    labels: (n_images,) true class indices
"""
from __future__ import annotations

import numpy as np


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Logits -> probabilities. Dividing by T > 1 softens (less confident), T < 1 sharpens."""
    z = logits / temperature
    z = z - z.max(axis=1, keepdims=True)  # subtract the max for numerical stability; result unchanged
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def nll(probs: np.ndarray, labels: np.ndarray) -> float:
    """Negative log-likelihood: average of -log(probability given to the TRUE class).
    Punishes confident mistakes very hard. Lower is better."""
    p_true = probs[np.arange(len(labels)), labels]
    return float(-np.log(np.clip(p_true, 1e-12, None)).mean())


def reliability_bins(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> dict[str, np.ndarray]:
    """Group predictions by confidence (0-6.7%, 6.7-13.3%, ...) and compare, per group,
    the average confidence with the actual accuracy."""
    conf = probs.max(axis=1)
    correct = probs.argmax(axis=1) == labels
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=True), 0, n_bins - 1)
    count = np.bincount(idx, minlength=n_bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        avg_conf = np.bincount(idx, weights=conf, minlength=n_bins) / count
        acc = np.bincount(idx, weights=correct, minlength=n_bins) / count
    return {"edges": edges, "count": count, "confidence": avg_conf, "accuracy": acc}


def ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """Expected Calibration Error: the average |confidence - accuracy| gap over the bins,
    weighted by how many images fall in each bin. 0 = perfectly honest."""
    b = reliability_bins(probs, labels, n_bins)
    used = b["count"] > 0
    gaps = np.abs(b["confidence"][used] - b["accuracy"][used])
    return float((gaps * b["count"][used]).sum() / b["count"].sum())


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Find the single number T that minimises NLL on the given labelled photos.

    Simple grid search over T in [0.05, 20] (log-spaced), then a finer grid around the best:
    easy to explain and accurate enough. Temperature never changes WHICH class is predicted,
    only HOW confident the model is, so accuracy stays the same.
    """
    grid = np.exp(np.linspace(np.log(0.05), np.log(20.0), 400))
    best = min(grid, key=lambda t: nll(softmax(logits, t), labels))
    fine = np.linspace(best * 0.97, best * 1.03, 61)
    return float(min(fine, key=lambda t: nll(softmax(logits, t), labels)))


def summary(probs: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    pred = probs.argmax(axis=1)
    return {
        "accuracy": round(float((pred == labels).mean()), 4),
        "mean_confidence": round(float(probs.max(axis=1).mean()), 4),
        "ece": round(ece(probs, labels), 4),
        "nll": round(nll(probs, labels), 4),
    }
