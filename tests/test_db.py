"""SQLite case store: create, update, chat messages, expert answers (uses a temp database)."""
from __future__ import annotations

from crop_doctor.app import db


def test_case_lifecycle(tmp_path):
    path = tmp_path / "t.db"
    expert_case = {"status": "expert", "seed": 1, "shortlist": ["tomato_septoria", "tomato_early_blight"]}
    cid = db.create_case("s1", "tomato", "a.jpg", expert_case, db_path=path)
    assert db.get_case(cid, db_path=path)["status"] == "pending"
    assert [c["id"] for c in db.list_cases("pending", db_path=path)] == [cid]

    db.add_message(cid, "farmer", "photo", db_path=path)
    db.add_message(cid, "assistant", "sent to expert", {"used_llm": False}, db_path=path)
    msgs = db.messages(cid, db_path=path)
    assert [m["role"] for m in msgs] == ["farmer", "assistant"] and msgs[1]["meta"] == {"used_llm": False}

    db.expert_answer(cid, "tomato_septoria", "Remove lower leaves.", db_path=path)
    c = db.get_case(cid, db_path=path)
    assert c["status"] == "expert_answered" and c["expert_label"] == "tomato_septoria" and c["answered_at"]
    # A later assistant update must not undo the expert's answer.
    db.update_assessment(cid, {"status": "diagnosis", "seed": 1, "label": "tomato_septoria", "shortlist": []}, db_path=path)
    assert db.get_case(cid, db_path=path)["status"] == "expert_answered"


def test_status_mapping_and_images(tmp_path):
    assert db.case_status({"status": "diagnosis"}) == "answered"
    assert db.case_status({"status": "question"}) == "answered"
    assert db.case_status({"status": "retake"}) == "retake"
    name = db.save_image(b"\xff\xd8fake", db_path=tmp_path / "i.db")
    assert db.load_image(name, db_path=tmp_path / "i.db") == b"\xff\xd8fake"


def test_postgres_url_is_normalised(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host.supabase.co:6543/postgres")
    assert db.database_url() == "postgresql+psycopg://u:p@host.supabase.co:6543/postgres"
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/db")
    assert db.database_url().startswith("postgresql+psycopg://")
    monkeypatch.delenv("DATABASE_URL")
    assert db.database_url().startswith("sqlite:///")
