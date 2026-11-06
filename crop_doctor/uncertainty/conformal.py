"""Conformal prediction: turn the model's probabilities into a SHORTLIST of diseases that contains
the true disease with a chosen probability (e.g. 90%).

Method: APS ("Adaptive Prediction Sets", Romano et al. 2020; tutorial: Angelopoulos & Bates).

1. Calibration (needs n labelled photos):
   For each photo, sort the classes from most to least likely and add up probabilities until you
   reach the TRUE class. That running total is the photo's "non-conformity score": high = the model
   had to go far down its list to find the truth.
2. q-hat = a slightly-above-90% quantile of those n scores.
3. For a new photo: walk down its sorted list and keep adding classes until the running total
   reaches q-hat. Those classes are the shortlist.

Guarantee: if the new photos are "exchangeable" with the calibration photos (same distribution),
the shortlist contains the true disease at least 90% of the time. Calibrated on LAB photos and
used on FIELD photos, the guarantee is void, and we measure how badly it breaks (Exp 4).
"""
from __future__ import annotations

import math

import numpy as np


def _sorted_cumsum(probs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(-probs, axis=1, kind="stable")
    cum = np.cumsum(np.take_along_axis(probs, order, axis=1), axis=1)
    return order, cum


def aps_scores(probs: np.ndarray, labels: np.ndarray, u: np.ndarray | None = None) -> np.ndarray:
    """Probability mass of the classes ranked above the true class, plus u * p(true class).

    u = None -> u = 1 (plain APS: mass at or above the true class).
    u ~ Uniform(0,1) -> randomised APS: a seeded "coin flip" for how much of the true class's own
    probability counts. It makes coverage exactly 90% instead of "at least 90%". Without it, a model that is
    99.9% sure of everything gets a threshold of ~0.999 and huge shortlists.
    """
    order, cum = _sorted_cumsum(probs)
    rank_of_true = np.argmax(order == labels[:, None], axis=1)
    p_true = probs[np.arange(len(labels)), labels]
    mass_above = cum[np.arange(len(labels)), rank_of_true] - p_true
    return mass_above + (1.0 if u is None else u) * p_true


def uniform_noise(n: int, seed: int) -> np.ndarray:
    """Reproducible u values for randomised APS (same seed -> same shortlists)."""
    return np.random.default_rng(seed).uniform(size=n)


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """The ceil((n+1)(1-alpha))-th smallest score. The "+1" is the finite-sample correction that makes
    the guarantee hold exactly. With too few calibration photos (e.g. n < 9 for alpha=0.1) no finite
    threshold is safe, so we return +inf, which means "shortlist = every class"."""
    n = len(scores)
    k = math.ceil((n + 1) * (1 - alpha))
    if n == 0 or k > n:
        return float("inf")
    return float(np.sort(scores)[k - 1])


def prediction_sets(probs: np.ndarray, qhat: float, u: np.ndarray | None = None) -> np.ndarray:
    """Boolean matrix (n_photos, n_classes): True = class is in the shortlist.

    u = None (plain APS): include a class if the mass ranked strictly ABOVE it is below q-hat. The top class
    is always included, so sets are never empty. Slightly conservative.
    u given (randomised APS): include class j if mass_above(j) + u * p(j) <= q-hat, the exact mirror of the
    score. Sets can be EMPTY: "this photo doesn't look like anything I was calibrated on". The app treats
    that as "send to an expert".
    """
    order, cum = _sorted_cumsum(probs)
    p_sorted = np.take_along_axis(probs, order, axis=1)
    mass_above = cum - p_sorted
    if u is None:
        keep_sorted = mass_above < qhat
    else:
        keep_sorted = mass_above + u[:, None] * p_sorted <= qhat
    sets = np.zeros_like(probs, dtype=bool)
    np.put_along_axis(sets, order, keep_sorted, axis=1)
    return sets


def group_quantiles(probs: np.ndarray, labels: np.ndarray, groups: np.ndarray, alpha: float,
                    u: np.ndarray | None = None) -> dict[str, float]:
    """Mondrian conformal: a separate q-hat for each group (here: each crop), from that group's photos only.

    One shared q-hat only promises 90% coverage ON AVERAGE over the mix of calibration photos; if one crop's
    photos are easy and plentiful, the other crop can end up well below 90%. Calibrating per crop gives each
    crop its own 90% promise. Usable because the farmer tells us the crop. A crop with too few calibration
    photos gets q-hat = inf (every disease stays possible -> expert)."""
    out = {}
    for g in np.unique(groups):
        m = groups == g
        out[str(g)] = conformal_quantile(aps_scores(probs[m], labels[m], None if u is None else u[m]), alpha)
    return out


def group_prediction_sets(probs: np.ndarray, qhats: dict[str, float], groups: np.ndarray,
                          u: np.ndarray | None = None) -> np.ndarray:
    sets = np.zeros_like(probs, dtype=bool)
    for g in np.unique(groups):
        m = groups == g
        sets[m] = prediction_sets(probs[m], qhats.get(str(g), float("inf")), None if u is None else u[m])
    return sets


def evaluate_sets(sets: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """Coverage, average shortlist size, and what an app would do with them.

    App rule: shortlist of exactly 1 disease -> answer; 2-3 -> follow-up question; empty or long -> expert.
    """
    covered = sets[np.arange(len(labels)), labels]
    size = sets.sum(axis=1)
    single = size == 1
    return {
        "coverage": float(covered.mean()),
        "avg_set_size": float(size.mean()),
        "empty_rate": float((size == 0).mean()),
        "answered_rate": float(single.mean()),                                   # sets of size 1
        "answered_accuracy": float(covered[single].mean()) if single.any() else float("nan"),
    }


def class_coverage(sets: np.ndarray, labels: np.ndarray, n_classes: int) -> np.ndarray:
    covered = sets[np.arange(len(labels)), labels]
    return np.array([covered[labels == c].mean() if (labels == c).any() else np.nan for c in range(n_classes)])
