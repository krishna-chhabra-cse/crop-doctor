"""Tests for the quality gate, severity estimate, knowledge file and decision logic (no model needed)."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from crop_doctor.assistant.decision import apply_answer, choose_question, decide, knowledge, urgency
from crop_doctor.config import CLASS_MAP
from crop_doctor.vision_extras import quality_gate, severity

CLASSES = sorted([c for c in CLASS_MAP if c != "tomato_spider_mites"] + ["potato_healthy", "tomato_something_else"])


def _leaf(lesion_radius: int = 0, size: int = 400) -> Image.Image:
    """Green leaf (ellipse) on a grey background with a sharp texture, optional brown lesion in the middle."""
    img = Image.new("RGB", (size, size), (128, 128, 128))
    d = ImageDraw.Draw(img)
    d.ellipse([40, 60, size - 40, size - 60], fill=(40, 140, 40))
    for x in range(int(size * 0.3), int(size * 0.7), 12):  # veins (inside the leaf) give the photo sharp edges
        d.line([(x, int(size * 0.3)), (x, int(size * 0.7))], fill=(25, 100, 25), width=2)
    if lesion_radius:
        c = size // 2
        d.ellipse([c - lesion_radius, c - lesion_radius, c + lesion_radius, c + lesion_radius], fill=(120, 70, 30))
    return img


def test_gate_accepts_good_leaf_and_rejects_bad_photos():
    assert quality_gate.check(_leaf()).ok
    assert "too_dark" in quality_gate.check(Image.new("RGB", (400, 400), (5, 5, 5))).problems
    assert "no_leaf" in quality_gate.check(Image.new("RGB", (400, 400), (30, 60, 200))).problems
    assert "blurry" in quality_gate.check(_leaf().filter(ImageFilter.GaussianBlur(12))).problems
    assert "too_small" in quality_gate.check(_leaf().resize((100, 100))).problems
    assert quality_gate.check(Image.new("RGB", (400, 400), (5, 5, 5))).message  # farmer gets a tip


def test_severity_grows_with_lesion_and_ignores_background():
    healthy = severity.estimate(_leaf())
    small = severity.estimate(_leaf(lesion_radius=30))
    big = severity.estimate(_leaf(lesion_radius=110))
    assert healthy["fraction"] < 0.05 and healthy["band"] == "mild"
    assert small["fraction"] < big["fraction"]
    assert big["band"] in ("moderate", "severe")
    assert severity.estimate(Image.new("RGB", (400, 400), (128, 128, 128)))["band"] == "unknown"


def test_knowledge_file_is_consistent():
    k = knowledge()
    assert set(k["diseases"]) == set(CLASSES)
    for q in k["follow_up_questions"]:
        for o in q["options"]:
            assert set(o["favours"]) <= set(CLASSES), (q["id"], o["favours"])


def test_urgency_rules():
    assert urgency("tomato_late_blight")["level"] == "urgent"            # fast spreader: always urgent
    assert urgency("tomato_healthy")["level"] == "none"
    assert urgency("tomato_septoria", extent="few", severity_band="mild")["level"] == "routine"
    assert urgency("tomato_septoria", extent="many")["level"] == "urgent"
    assert urgency("tomato_septoria", severity_band="severe")["level"] == "urgent"   # photo as tie-breaker
    assert urgency("tomato_yellow_curl_virus", extent="many")["level"] == "urgent"


def test_question_choice_and_bayes_update():
    q = choose_question(["tomato_early_blight", "tomato_septoria"])
    assert q is not None and q["id"] == "rings_vs_small_spots"
    assert choose_question(["tomato_early_blight"]) is None             # nothing to separate
    probs = np.array([0.5, 0.5])
    post = apply_answer(probs, ["a", "b"], ["a"], trust=0.8)
    assert np.allclose(post, [0.8, 0.2])


def _probs(d: dict) -> np.ndarray:
    p = np.array([d.get(c, 0.0) for c in CLASSES])
    return p / p.sum()


def test_decide_paths():
    confident = _probs({"tomato_septoria": 0.97, "tomato_early_blight": 0.03})
    assert decide(confident, CLASSES, qhat=0.9, u=0.5)["status"] == "diagnosis"

    healthy = _probs({"tomato_healthy": 0.97, "tomato_early_blight": 0.03})
    assert decide(healthy, CLASSES, qhat=0.9, u=0.5)["status"] == "healthy"

    two = _probs({"tomato_septoria": 0.5, "tomato_early_blight": 0.45, "tomato_late_blight": 0.05})
    r = decide(two, CLASSES, qhat=0.9, u=0.5)
    assert r["status"] == "question" and len(r["shortlist"]) in (2, 3)
    # Farmer says "rings like a target" -> early blight wins after Bayes update.
    fav = r["question"]["options"][0]["favours"]
    r2 = decide(two, CLASSES, qhat=0.9, u=0.5, answer={"question_id": r["question"]["id"], "favours": fav},
                asked={r["question"]["id"]})
    assert r2["status"] == "diagnosis" and r2["label"] == "tomato_early_blight"

    flat = _probs({c: 1.0 for c in CLASSES if c.startswith("tomato")})
    assert decide(flat, CLASSES, qhat=0.9, u=0.5)["status"] == "expert"
