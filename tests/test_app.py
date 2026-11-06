"""Headless UI tests with Streamlit's AppTest: the farmer chat page runs every demo sample end to end.

These load the real model (a few seconds) and write to a temporary database.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from crop_doctor.app import db

PAGE = str(Path(__file__).resolve().parents[1] / "crop_doctor" / "app" / "pages" / "1_Farmer_Chat.py")
HOME = str(Path(__file__).resolve().parents[1] / "crop_doctor" / "app" / "Home.py")
SAMPLES = json.loads((Path(PAGE).parents[1] / "samples" / "samples.json").read_text())


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(db, "IMAGES", tmp_path / "images")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def run_sample(title: str) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=120).run()
    next(s for s in at.selectbox if s.label.startswith("Demo photos")).select(title).run()
    next(b for b in at.button if b.label == "Use this sample").click().run()
    assert not at.exception, at.exception
    return at


def test_home_page_renders():
    at = AppTest.from_file(HOME, default_timeout=60).run()
    assert not at.exception and at.title[0].value == "Crop Doctor"


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["file"] for s in SAMPLES])
def test_each_sample_reaches_its_expected_outcome(sample):
    at = run_sample(sample["title"])
    case = db.list_cases()[-1]
    assert case["assessment"]["status"] == sample["expected_status"]
    texts = " ".join(m.markdown[0].value for m in at.chat_message if m.markdown)
    if sample["expected_status"] == "diagnosis":
        assert "Most likely" in texts and any(b.label == "Many plants" for b in at.button)
    if sample["expected_status"] == "expert":
        assert case["status"] == "pending"


def test_question_flow_then_answer():
    s = next(s for s in SAMPLES if s["expected_status"] == "question")
    at = run_sample(s["title"])
    opts = [b for b in at.button if b.key and b.key.startswith("opt") and b.key != "opt_none"]
    assert opts
    opts[0].click().run()
    assert not at.exception
    case = db.list_cases()[-1]
    assert case["assessment"]["status"] in ("diagnosis", "expert", "healthy")
    assert [m["role"] for m in db.messages(case["id"])][-2:] == ["farmer", "assistant"]


DASH = str(Path(PAGE).parent / "2_Expert_Dashboard.py")


def test_expert_answers_a_pending_case_and_farmer_sees_it():
    s = next(s for s in SAMPLES if s["expected_status"] == "expert")
    farmer = run_sample(s["title"])
    case = db.list_cases()[-1]
    assert [c["id"] for c in db.expert_queue()] == [case["id"]]

    dash = AppTest.from_file(DASH, default_timeout=180).run()
    assert not dash.exception, dash.exception
    dash.text_area[0].input("Remove lower leaves, spray copper this week.")
    next(b for b in dash.button if b.label == "Send answer to farmer").click().run()
    assert not dash.exception
    case = db.get_case(case["id"])
    assert case["status"] == "expert_answered" and case["expert_label"]
    assert db.expert_queue() == []
    # Not a random audit -> must NOT change the calibration set.
    assert not [p for p in db.calibration_points() if p["source"] == "expert_audit"]

    farmer.run()
    texts = " ".join(m.markdown[0].value for m in farmer.chat_message if m.markdown)
    assert "Expert:" in texts and "spray copper" in texts


def test_random_audit_recalibrates_instantly():
    s = next(s for s in SAMPLES if s["expected_status"] == "diagnosis")
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.session_state["audit_rate"] = 1.0                      # demo: audit every answered photo
    at.run()
    next(x for x in at.selectbox if x.label.startswith("Demo photos")).select(s["title"]).run()
    next(b for b in at.button if b.label == "Use this sample").click().run()
    case = db.list_cases()[-1]
    assert case["audit"] == 1 and db.expert_queue()[0]["id"] == case["id"]

    runs_before = len(db.calibration_runs())
    dash = AppTest.from_file(DASH, default_timeout=180).run()
    next(b for b in dash.button if b.label == "Send answer to farmer").click().run()
    assert not dash.exception
    pts = [p for p in db.calibration_points() if p["source"] == "expert_audit"]
    assert len(pts) == 1 and pts[0]["case_id"] == case["id"]
    assert len(db.calibration_runs()) == runs_before + 1


def test_trust_meter_demo_controls():
    dash = AppTest.from_file(DASH, default_timeout=180).run()
    assert not dash.exception, dash.exception
    next(b for b in dash.button if b.label == "Reset: lab photos only").click().run()
    lab_run = db.calibration_runs()[-1]
    assert lab_run["n_field_points"] == 0
    for _ in range(3):
        next(b for b in dash.button if b.label == "Add 10 simulated expert labels").click().run()
    assert not dash.exception
    run = db.calibration_runs()[-1]
    assert run["n_field_points"] == 30
    assert run["monitor_coverage"] > lab_run["monitor_coverage"] + 0.3   # the broken promise gets repaired


def test_follow_up_chat_question():
    s = next(s for s in SAMPLES if s["expected_status"] == "diagnosis")
    at = run_sample(s["title"])
    at.chat_input[0].set_value("Can I use an organic spray?").run()
    assert not at.exception
    last = db.messages(db.list_cases()[-1]["id"])[-1]
    assert last["role"] == "assistant" and last["meta"]["sources"]
