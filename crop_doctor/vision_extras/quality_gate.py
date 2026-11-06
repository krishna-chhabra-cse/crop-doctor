"""Photo quality gate: reject photos the model shouldn't even try to judge, and tell the farmer how to retake.

Checks (cheap, no neural network):
- too small : short side under MIN_SIDE pixels
- too dark / too bright : average brightness outside a sensible range
- blurry : variance of the Laplacian (an edge detector). Sharp photo = many strong edges = high variance
- no leaf : too few "plant-coloured" pixels (green / yellow / brown with enough colour saturation)

Thresholds were checked on real photos (see `validate()`): they should pass almost all PlantDoc
field photos while catching clearly unusable ones. They are deliberately lenient: a borderline photo goes
to the model, and the conformal shortlist / expert queue handles the rest.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image

MIN_SIDE = 150
DARK, BRIGHT = 35, 230          # mean of the V (brightness) channel, 0-255
BLUR_THRESHOLD = 25.0           # variance of Laplacian on a 512-px version of the photo
MIN_PLANT_FRACTION = 0.06      # lowest real field photo had ~18%; 6% still rejects non-leaf photos

RETAKE_TIPS = {
    "too_small": "The photo is too small. Please send the original photo, not a thumbnail.",
    "too_dark": "The photo is too dark. Please take it in daylight, without shade over the leaf.",
    "too_bright": "The photo is too bright. Avoid direct sun glare; shade the leaf with your hand.",
    "blurry": "The photo is blurry. Hold the phone steady, tap the leaf on screen to focus, then take it.",
    "no_leaf": "I can't find a leaf in this photo. Please photograph one affected leaf filling most of the frame.",
}


@dataclass
class GateResult:
    ok: bool
    problems: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def message(self) -> str:
        return " ".join(RETAKE_TIPS[p] for p in self.problems)


def to_bgr(img: Image.Image, long_side: int = 512) -> np.ndarray:
    """PIL RGB -> OpenCV BGR array, resized so the long side is `long_side` (makes thresholds size-independent)."""
    img = img.convert("RGB")
    scale = long_side / max(img.size)
    if scale < 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.BILINEAR)
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


def plant_mask(hsv: np.ndarray) -> np.ndarray:
    """Pixels coloured like a leaf: green, yellow or brown (OpenCV hue 0-180) with some saturation."""
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return (h >= 5) & (h <= 95) & (s >= 40) & (v >= 30)


def check(img: Image.Image) -> GateResult:
    problems = []
    if min(img.size) < MIN_SIDE:
        problems.append("too_small")
    bgr = to_bgr(img)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    brightness = float(hsv[..., 2].mean())
    sharpness = float(cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
    plant = float(plant_mask(hsv).mean())
    if brightness < DARK:
        problems.append("too_dark")
    elif brightness > BRIGHT:
        problems.append("too_bright")
    if sharpness < BLUR_THRESHOLD:
        problems.append("blurry")
    if plant < MIN_PLANT_FRACTION:
        problems.append("no_leaf")
    return GateResult(ok=not problems, problems=problems,
                      metrics={"brightness": round(brightness, 1), "sharpness": round(sharpness, 1),
                               "plant_fraction": round(plant, 3)})
