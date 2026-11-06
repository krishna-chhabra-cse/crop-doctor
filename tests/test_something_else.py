"""Exp 10: the 12th class "something else" (a tomato problem the model wasn't taught) always goes to an expert."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from crop_doctor.assistant.decision import SOMETHING_ELSE, decide, knowledge
from crop_doctor.assistant.llm import mentions_forbidden_disease
from crop_doctor.assistant.pipeline import CropDoctor
from crop_doctor.model.crops import crop_mask

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "crop_doctor" / "app" / "samples" / "diag_tomato.jpg"
CLASSES = json.loads((ROOT / "crop_doctor" / "data" / "splits_v3" / "classes.json").read_text())
TOMATO = crop_mask(CLASSES, "tomato")


def probs_with(winner: str, p: float, runner_up: str | None = None, p2: float = 0.0) -> np.ndarray:
    out = np.zeros(len(CLASSES))
    rest = [i for i in np.nonzero(TOMATO)[0] if CLASSES[i] not in (winner, runner_up)]
    out[CLASSES.index(winner)] = p
    if runner_up:
        out[CLASSES.index(runner_up)] = p2
    out[rest] = (1 - p - p2) / len(rest)
    return out


def test_something_else_is_a_known_tomato_entry():
    d = knowledge()["diseases"][SOMETHING_ELSE]
    assert d["crop"] == "tomato" and d["name"]
    assert not crop_mask(CLASSES, "potato")[CLASSES.index(SOMETHING_ELSE)]     # masked out for potato photos


def test_top_answer_something_else_goes_to_expert_never_a_diagnosis():
    r = decide(probs_with(SOMETHING_ELSE, 0.9), CLASSES, qhat=0.9, u=0.5)
    assert r["status"] == "expert" and r["something_else"] is True
    assert "label" not in r and "different problem" in r["reason"]


def test_known_disease_on_top_is_unchanged():
    r = decide(probs_with("tomato_late_blight", 0.97), CLASSES, qhat=0.9, u=0.5)
    assert r["status"] == "diagnosis" and r["label"] == "tomato_late_blight" and not r.get("something_else")


def test_follow_up_answer_never_turns_something_else_into_a_diagnosis():
    # Shortlist: something else + early blight; the farmer's answer favours neither -> still "something else".
    p = probs_with("tomato_early_blight", 0.45, SOMETHING_ELSE, 0.5)
    r = decide(p, CLASSES, qhat=0.99, u=0.5, answer={"question_id": "x", "favours": ["tomato_septoria"]})
    assert r["status"] == "expert" and "label" not in r


class FakeBackend:
    classes = CLASSES

    def raw_logits(self, img):
        out = np.zeros(len(CLASSES))
        out[CLASSES.index(SOMETHING_ELSE)] = 10.0
        return out


def test_pipeline_routes_something_else_to_expert_with_the_unusual_photo_flag(tmp_path):
    cfg = tmp_path / "app.json"
    cfg.write_text(json.dumps({"classes": CLASSES, "temperature": 1.0, "qhat": {"0.1": {"potato": 0.9, "tomato": 0.9}}}))
    doc = CropDoctor(backend=FakeBackend(), app_config=cfg)
    assert doc.crops == ["potato", "tomato"]
    r = doc.assess(Image.open(SAMPLE), "tomato", seed=1)
    assert r["status"] == "expert" and r["something_else"] and r["unfamiliar"]
    assert r.get("question") is None and "label" not in r
    assert "expert" in r["message"] and "A different tomato problem" not in r["message"]
    # On potato the class is masked out, so it can never fire.
    assert doc.assess(Image.open(SAMPLE), "potato", seed=1).get("something_else") is None


def test_llm_guard_does_not_treat_something_else_as_a_forbidden_disease():
    assert mentions_forbidden_disease("This looks like a different tomato problem.", ["tomato_late_blight"]) is None


def test_something_else_gets_only_general_safety_notes_not_another_diseases_treatment():
    from crop_doctor.assistant.llm import gather_notes
    notes = gather_notes({"status": "expert", "something_else": True,
                          "shortlist": [SOMETHING_ELSE, "tomato_early_blight"]}, None)
    assert notes and all(c.disease == "general" for c in notes)
