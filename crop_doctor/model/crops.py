"""Crop-aware prediction: the farmer tells us the crop, so we only consider that crop's diseases.

A potato leaf can't have a tomato disease. Day 3 showed the lab model often predicts a tomato
disease for potato photos; removing impossible answers is free accuracy.
"""
from __future__ import annotations

import numpy as np


def crop_of(label: str) -> str:
    return label.split("_", 1)[0]          # "tomato_late_blight" -> "tomato"


def crop_mask(classes: list[str], crop: str) -> np.ndarray:
    """Boolean vector: True for the classes that belong to `crop`."""
    return np.array([crop_of(c) == crop for c in classes])


def mask_logits(logits: np.ndarray, classes: list[str], crops: list[str] | np.ndarray) -> np.ndarray:
    """Set the logits of other crops' diseases to -inf (softmax then gives them probability 0).

    logits: (n, n_classes); crops: the crop for each photo, e.g. ["tomato", "potato", ...].
    """
    out = logits.astype(np.float64).copy()
    for crop in set(crops):
        rows = np.asarray(crops) == crop
        out[np.ix_(rows, ~crop_mask(classes, crop))] = -np.inf
    return out


def crops_from_labels(labels: np.ndarray, classes: list[str]) -> np.ndarray:
    """In experiments the farmer's answer = the crop of the true label."""
    return np.array([crop_of(classes[y]) for y in labels])
