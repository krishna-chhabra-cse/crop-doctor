"""Unfamiliar-photo gate (Exp 9): a photo that doesn't strongly match ANY known disease goes to an expert."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from crop_doctor.assistant.pipeline import CropDoctor

SAMPLE = Path(__file__).resolve().parents[1] / "crop_doctor" / "app" / "samples" / "diag_tomato.jpg"
CLASSES = json.loads((Path(__file__).resolve().parents[1] / "server" / "assets" / "app_model.json").read_text())["classes"]


class FakeBackend:
    classes = CLASSES

    def __init__(self, strength: float):
        self.strength = strength

    def raw_logits(self, img):
        out = np.zeros(len(CLASSES))
        out[CLASSES.index("tomato_late_blight")] = self.strength     # one clear winner
        return out


def doctor(tmp_path, strength: float, threshold: float | None) -> CropDoctor:
    cfg = {"classes": CLASSES, "temperature": 1.0, "qhat": {"0.1": {"potato": 0.9, "tomato": 0.9}}}
    if threshold is not None:
        cfg["unfamiliar"] = {"score": "energy", "threshold": {"potato": threshold, "tomato": threshold}}
    path = tmp_path / "app.json"
    path.write_text(json.dumps(cfg))
    return CropDoctor(backend=FakeBackend(strength), app_config=path)


def test_familiar_photo_gets_an_answer(tmp_path):
    r = doctor(tmp_path, strength=12.0, threshold=5.0).assess(Image.open(SAMPLE), "tomato", seed=1)
    assert r["status"] == "diagnosis" and r["label"] == "tomato_late_blight" and not r.get("unfamiliar")
    assert r["familiarity"] > 5.0


def test_unfamiliar_photo_goes_to_expert_even_if_one_class_wins(tmp_path):
    # Same winner, but every output is weak: energy below the threshold.
    r = doctor(tmp_path, strength=3.0, threshold=5.0).assess(Image.open(SAMPLE), "tomato", seed=1)
    assert r["status"] == "expert" and r["unfamiliar"] is True
    assert "label" not in r and "probability" not in r
    assert r.get("question") is None
    assert "doesn't look much like" in r["message"]


def test_no_threshold_means_no_gate(tmp_path):
    r = doctor(tmp_path, strength=3.0, threshold=None).assess(Image.open(SAMPLE), "tomato", seed=1)
    assert not r.get("unfamiliar") and r["familiarity"] < 5.0
