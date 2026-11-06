"""The website's API, end to end with FastAPI's TestClient (real model, temporary database)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from crop_doctor.app import db


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(db, "DB_PATH", tmp_path_factory.mktemp("api") / "api.db")
    mp.delenv("ANTHROPIC_API_KEY", raising=False)
    mp.setenv("EXPERT_KEY", "test-key")
    from server.main import app
    with TestClient(app) as c:
        yield c
    mp.undo()


EXPERT = {"X-Expert-Key": "test-key"}


def sample(client, title_part: str) -> dict:
    s = next(s for s in client.get("/api/meta").json()["samples"] if title_part in s["title"])
    r = client.post("/api/cases", data={"crop": s["crop"], "sample": s["file"]}, headers={"X-Session-Id": "t1"})
    assert r.status_code == 200, r.text
    return r.json()


def test_meta_and_health(client):
    assert client.get("/api/health").json()["ok"]
    m = client.get("/api/meta").json()
    assert set(m["crops"]) == {"tomato", "potato"} and m["samples"] and m["expert_key_required"]


def test_upload_flow_diagnosis_extent_and_question(client):
    c = sample(client, "clear case")
    assert c["assessment"]["status"] == "diagnosis" and c["assessment"]["disease"]["name"]
    assert c["ask_extent"] and c["messages"][0]["image"].startswith("/api/images/")
    assert client.get(c["messages"][0]["image"]).status_code == 200
    c2 = client.post(f"/api/cases/{c['id']}/extent", json={"value": "many"}).json()
    assert c2["assessment"]["urgency"]["level"] == "urgent" and not c2["ask_extent"]
    c3 = client.post(f"/api/cases/{c['id']}/messages", json={"text": "Can I use an organic spray?"}).json()
    assert c3["messages"][-1]["role"] == "assistant" and c3["messages"][-1]["sources"]


def test_question_flow(client):
    c = sample(client, "needs one question")
    assert c["assessment"]["status"] == "question" and c["assessment"]["question"]["options"]
    c2 = client.post(f"/api/cases/{c['id']}/question", json={"option": 0}).json()
    assert c2["assessment"]["status"] in ("diagnosis", "expert", "healthy")
    assert client.post(f"/api/cases/{c['id']}/question", json={"option": 0}).status_code == 409


def test_bad_inputs(client):
    assert client.post("/api/cases", data={"crop": "banana"}).status_code == 400
    assert client.post("/api/cases", data={"crop": "tomato"}, files={"file": ("x.jpg", b"not an image")}).status_code == 400
    assert client.get("/api/cases/99999").status_code == 404
    assert client.get("/api/samples/../../config.py").status_code == 404


def test_expert_endpoints_need_the_key_and_work(client):
    assert client.get("/api/expert/queue").status_code == 401
    c = sample(client, "goes to expert")
    queue = client.get("/api/expert/queue", headers=EXPERT).json()
    item = next(q for q in queue if q["id"] == c["id"])
    assert item["kind"] == "unsure" and item["options"]
    r = client.post(f"/api/expert/cases/{c['id']}", json={"label": item["options"][0]["label"], "note": "Remove leaves."},
                    headers=EXPERT).json()
    assert r["recalibrated"] is False                       # not a random audit -> no recalibration
    farmer = client.get(f"/api/cases/{c['id']}").json()
    assert farmer["status"] == "expert_answered" and farmer["messages"][-1]["role"] == "expert"
    assert client.get("/api/expert/answered", headers=EXPERT).json()["retraining_pool"] >= 1


def test_trust_meter_controls(client):
    t = client.post("/api/expert/calibration", json={"action": "reset_lab"}, headers=EXPERT).json()
    assert t["current"]["n_field_points"] == 0
    t = client.post("/api/expert/calibration", json={"action": "simulate", "k": 20}, headers=EXPERT).json()
    assert t["current"]["n_field_points"] == 20 and len(t["since_reset"]) == 2
    t = client.post("/api/expert/calibration", json={"action": "reset_field"}, headers=EXPERT).json()
    assert t["current"]["monitor_coverage"] > 0.85
