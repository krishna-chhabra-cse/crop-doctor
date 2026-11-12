"""Choosing which field photos an expert should label (used by Experiment 11).

Calibration photos are set aside at random BEFORE any picking. Conformal's 90% promise needs
calibration photos that look like future photos, so hand-picked "hard" photos must never reach it.
"""
from __future__ import annotations

import numpy as np

STRATEGIES = ("random", "uncertain")


def split_pool(n_photos: int, n_cal: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Randomly divide photo indices into (pickable, calibration); the two never overlap."""
    if not 0 < n_cal < n_photos:
        raise ValueError("n_cal must be between 1 and n_photos - 1")
    order = np.random.default_rng(seed).permutation(n_photos)
    return order[n_cal:], order[:n_cal]


def entropy(probs: np.ndarray) -> np.ndarray:
    """Uncertainty of each prediction: 0 when certain, highest when spread across all classes."""
    p = np.clip(probs, 1e-12, 1.0)
    return -(p * np.log(p)).sum(axis=1)


def pick_for_labelling(strategy: str, probs: np.ndarray, candidates: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Return n distinct photo indices from candidates. probs is indexed by photo, over the whole pool."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy}")
    if n > len(candidates):
        raise ValueError("budget is larger than the number of candidate photos")
    rng = np.random.default_rng(seed)
    if strategy == "random":
        return rng.choice(candidates, n, replace=False)
    # Shuffle first so that ties are not decided by photo order.
    shuffled = rng.permutation(candidates)
    return shuffled[np.argsort(-entropy(probs[shuffled]), kind="stable")[:n]]
