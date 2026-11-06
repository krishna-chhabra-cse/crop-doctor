"""Rough severity estimate: what share of the leaf is diseased (brown / yellow / dark) rather than green?

1. Green pixels = healthy leaf tissue.
2. "Close" the green mask (fill small gaps) and fill holes, giving the leaf's outline. Lesions INSIDE the
   leaf are now part of the leaf area, but brown soil around the leaf is not.
3. Lesion pixels = inside the leaf outline but not green.
4. severity = lesion area / leaf area -> mild (< 10%), moderate (10-25%), severe (> 25%).

This is an ESTIMATE from colour only. It is checked against PlantVillage (healthy leaves should score low)
in `validate()`, and the app always labels it "estimate".
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from crop_doctor.vision_extras.quality_gate import to_bgr

BANDS = [(0.10, "mild"), (0.25, "moderate"), (1.01, "severe")]


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    big = [c for c in contours if cv2.contourArea(c) >= 0.01 * mask.size]  # ignore specks
    cv2.drawContours(filled, big, -1, 255, thickness=cv2.FILLED)
    return filled


def estimate(img: Image.Image) -> dict:
    hsv = cv2.cvtColor(to_bgr(img), cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = ((h >= 33) & (h <= 90) & (s >= 35) & (v >= 35)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    leaf = _fill_holes(cv2.morphologyEx(green, cv2.MORPH_CLOSE, kernel)) > 0
    leaf_px = int(leaf.sum())
    if leaf_px < 0.05 * leaf.size:
        return {"fraction": None, "band": "unknown", "leaf_fraction_of_photo": round(leaf_px / leaf.size, 3)}
    lesion = leaf & (green == 0)
    frac = float(lesion.sum() / leaf_px)
    band = next(name for limit, name in BANDS if frac < limit)
    return {"fraction": round(frac, 3), "band": band, "leaf_fraction_of_photo": round(leaf_px / leaf.size, 3)}
