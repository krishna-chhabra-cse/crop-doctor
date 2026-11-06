"""SQLite storage for the app: every farmer photo is a "case" with its chat messages.

    cases     one row per photo: crop, image file, the assistant's decision, status, expert's answer
    messages  the chat for a case: who said what, when

Status flow:  answered (assistant answered)  |  pending (waiting for an expert)  ->  expert_answered
SQLite is a single file (app_data/crop_doctor.db): zero setup, fine for a demo and a small pilot.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from crop_doctor import config

APP_DATA = config.ROOT / "app_data"
DB_PATH = APP_DATA / "crop_doctor.db"
IMAGES = APP_DATA / "images"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    session_id    TEXT NOT NULL,
    crop          TEXT NOT NULL,
    image_path    TEXT NOT NULL,
    seed          INTEGER NOT NULL,
    status        TEXT NOT NULL,          -- answered | pending | expert_answered | retake
    model_label   TEXT,                   -- assistant's most likely disease (if it answered)
    probability   REAL,
    shortlist     TEXT,                   -- JSON list
    assessment    TEXT NOT NULL,          -- full JSON from CropDoctor.assess()
    expert_label  TEXT,
    expert_note   TEXT,
    answered_at   TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id),
    created_at  TEXT NOT NULL,
    role        TEXT NOT NULL,            -- farmer | assistant | expert
    text        TEXT NOT NULL,
    meta        TEXT                      -- JSON: sources, used_llm, ...
);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_messages_case ON messages(case_id);
-- Live calibration (Day 8): the labelled photos the conformal threshold is computed from.
CREATE TABLE IF NOT EXISTS calibration_points (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    source      TEXT NOT NULL,            -- lab_val | field_cal | expert_audit | simulated_expert
    case_id     INTEGER,
    label_idx   INTEGER NOT NULL,
    logits      TEXT NOT NULL             -- JSON list, crop-masked model outputs
);
-- One row per recalibration: what the app used, and how it did on the monitor set (the trust meter).
CREATE TABLE IF NOT EXISTS calibration_runs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at        TEXT NOT NULL,
    n_points          INTEGER NOT NULL,
    n_field_points    INTEGER NOT NULL,
    temperature       REAL NOT NULL,
    qhat              REAL NOT NULL,      -- may be inf (too few photos: every disease stays possible)
    monitor_coverage  REAL,
    monitor_set_size  REAL,
    monitor_answered  REAL,
    note              TEXT
);
"""

AUDIT_RATE = 0.1   # share of photos the assistant answered that are ALSO sent to an expert, at random


def _migrate(con: sqlite3.Connection) -> None:
    """Databases created on Day 7 lack the audit column; add it in place."""
    cols = {r["name"] for r in con.execute("PRAGMA table_info(cases)")}
    if "audit" not in cols:
        con.execute("ALTER TABLE cases ADD COLUMN audit INTEGER NOT NULL DEFAULT 0")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(db_path: Path | None = None):
    db_path = db_path or DB_PATH          # looked up at call time, so tests can point it elsewhere
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def save_image(data: bytes, suffix: str = ".jpg", images_dir: Path | None = None) -> str:
    images_dir = images_dir or IMAGES
    images_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{suffix}"
    (images_dir / name).write_bytes(data)
    return name


def case_status(assessment: dict) -> str:
    return {"expert": "pending", "retake": "retake"}.get(assessment["status"], "answered")


def create_case(session_id: str, crop: str, image_path: str, assessment: dict, db_path: Path | None = None,
                audit: bool = False) -> int:
    """audit=True: the assistant answered, but this photo is ALSO randomly sent to an expert for checking.
    Random audits are an unbiased sample of what farmers send, so only they may recalibrate the conformal
    threshold (photos the assistant itself sent to experts are the hard ones, a biased sample)."""
    with connect(db_path) as con:
        cur = con.execute(
            "INSERT INTO cases (created_at, session_id, crop, image_path, seed, status, model_label, probability,"
            " shortlist, assessment, audit) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (now(), session_id, crop, image_path, assessment["seed"], case_status(assessment), assessment.get("label"),
             assessment.get("probability"), json.dumps(assessment.get("shortlist", [])), json.dumps(assessment),
             int(audit)))
        return int(cur.lastrowid)


def expert_queue(db_path: Path | None = None) -> list[dict]:
    """Cases waiting for an expert: those the assistant sent, plus random audits not yet checked."""
    with connect(db_path) as con:
        rows = con.execute("SELECT * FROM cases WHERE expert_label IS NULL AND (status='pending' OR "
                           "(audit=1 AND status='answered')) ORDER BY id").fetchall()
    return [_row(r) for r in rows]


def update_assessment(case_id: int, assessment: dict, db_path: Path | None = None) -> None:
    """After a follow-up answer or the extent question, the decision can change."""
    with connect(db_path) as con:
        row = con.execute("SELECT status FROM cases WHERE id=?", (case_id,)).fetchone()
        status = row["status"] if row["status"] == "expert_answered" else case_status(assessment)
        con.execute("UPDATE cases SET status=?, model_label=?, probability=?, shortlist=?, assessment=? WHERE id=?",
                    (status, assessment.get("label"), assessment.get("probability"),
                     json.dumps(assessment.get("shortlist", [])), json.dumps(assessment), case_id))


def add_message(case_id: int, role: str, text: str, meta: dict | None = None, db_path: Path | None = None) -> None:
    with connect(db_path) as con:
        con.execute("INSERT INTO messages (case_id, created_at, role, text, meta) VALUES (?,?,?,?,?)",
                    (case_id, now(), role, text, json.dumps(meta or {})))


def messages(case_id: int, db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        rows = con.execute("SELECT * FROM messages WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
    return [dict(r) | {"meta": json.loads(r["meta"] or "{}")} for r in rows]


def get_case(case_id: int, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as con:
        row = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return _row(row) if row else None


def list_cases(status: str | None = None, db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        q = "SELECT * FROM cases" + (" WHERE status=?" if status else "") + " ORDER BY id"
        rows = con.execute(q, (status,) if status else ()).fetchall()
    return [_row(r) for r in rows]


def expert_answer(case_id: int, label: str, note: str, db_path: Path | None = None) -> None:
    """Expert labels a case. The label is stored for recalibration/retraining (Day 8)."""
    with connect(db_path) as con:
        con.execute("UPDATE cases SET status='expert_answered', expert_label=?, expert_note=?, answered_at=? WHERE id=?",
                    (label, note, now(), case_id))


# ---------- live calibration storage ----------

def clear_calibration_points(db_path: Path | None = None) -> None:
    with connect(db_path) as con:
        con.execute("DELETE FROM calibration_points")


def add_calibration_points(rows: list[tuple[str, int | None, int, list[float]]], db_path: Path | None = None) -> None:
    """rows: (source, case_id, label_idx, logits)."""
    with connect(db_path) as con:
        con.executemany("INSERT INTO calibration_points (created_at, source, case_id, label_idx, logits) VALUES (?,?,?,?,?)",
                        [(now(), s, c, int(y), json.dumps([None if v == float("-inf") else float(v) for v in lg]))
                         for s, c, y, lg in rows])


def calibration_points(db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        rows = con.execute("SELECT * FROM calibration_points ORDER BY id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["logits"] = [float("-inf") if v is None else v for v in json.loads(d["logits"])]  # -inf = other crop
        out.append(d)
    return out


def add_calibration_run(run: dict, db_path: Path | None = None) -> None:
    with connect(db_path) as con:
        con.execute("INSERT INTO calibration_runs (created_at, n_points, n_field_points, temperature, qhat,"
                    " monitor_coverage, monitor_set_size, monitor_answered, note) VALUES (?,?,?,?,?,?,?,?,?)",
                    (now(), run["n_points"], run["n_field_points"], run["temperature"], run["qhat"],
                     run.get("monitor_coverage"), run.get("monitor_set_size"), run.get("monitor_answered"), run.get("note")))


def calibration_runs(db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        return [dict(r) for r in con.execute("SELECT * FROM calibration_runs ORDER BY id").fetchall()]


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["shortlist"] = json.loads(d["shortlist"] or "[]")
    d["assessment"] = json.loads(d["assessment"])
    return d
