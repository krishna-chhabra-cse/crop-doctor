"""Storage for the app: every farmer photo is a "case" with its chat messages.

    cases               one row per photo: crop, the assistant's decision, status, expert's answer
    messages            the chat for a case: who said what, when
    images              the photo bytes (kept in the database so they survive server restarts)
    calibration_points  labelled photos the conformal threshold is computed from (live recalibration)
    calibration_runs    one row per recalibration: settings + monitor results (the trust meter)

Status flow:  answered (assistant answered)  |  pending (waiting for an expert)  ->  expert_answered

Where the data lives:
- locally: a SQLite file (app_data/crop_doctor.db), zero setup;
- live site: Postgres on Supabase, chosen by setting the DATABASE_URL environment variable.
SQLAlchemy writes the same SQL for both, so the rest of the code doesn't care which one is used.
"""
from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from sqlalchemy import (
    Column, Float, Integer, LargeBinary, MetaData, String, Table, Text, create_engine, delete, insert, select, update,
)

from crop_doctor import config

APP_DATA = config.ROOT / "app_data"
DB_PATH = APP_DATA / "crop_doctor.db"
IMAGES = APP_DATA / "images"          # only used by save_image(images_dir=...) in old tests; photos live in the DB
AUDIT_RATE = 0.1   # share of photos the assistant answered that are ALSO sent to an expert, at random

meta = MetaData()
cases = Table(
    "cases", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", String(32), nullable=False),
    Column("session_id", String(64), nullable=False),
    Column("crop", String(32), nullable=False),
    Column("image_path", String(128), nullable=False),     # key into the images table
    Column("seed", Integer, nullable=False),
    Column("status", String(32), nullable=False, index=True),
    Column("model_label", String(64)),
    Column("probability", Float),
    Column("shortlist", Text),                               # JSON list
    Column("assessment", Text, nullable=False),             # full JSON from CropDoctor.assess()
    Column("expert_label", String(64)),
    Column("expert_note", Text),
    Column("answered_at", String(32)),
    Column("audit", Integer, nullable=False, default=0),
)
messages_t = Table(
    "messages", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", Integer, nullable=False, index=True),
    Column("created_at", String(32), nullable=False),
    Column("role", String(16), nullable=False),              # farmer | assistant | expert
    Column("text", Text, nullable=False),
    Column("meta", Text),                                    # JSON: sources, used_llm, ...
)
images_t = Table(
    "images", meta,
    Column("name", String(128), primary_key=True),
    Column("data", LargeBinary, nullable=False),
)
points_t = Table(
    "calibration_points", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", String(32), nullable=False),
    Column("source", String(32), nullable=False),            # lab_val | field_cal | expert_audit | simulated_expert
    Column("case_id", Integer),
    Column("label_idx", Integer, nullable=False),
    Column("logits", Text, nullable=False),                  # JSON list, crop-masked model outputs
)
runs_t = Table(
    "calibration_runs", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", String(32), nullable=False),
    Column("n_points", Integer, nullable=False),
    Column("n_field_points", Integer, nullable=False),
    Column("temperature", Float, nullable=False),
    Column("qhat", Float, nullable=False),                   # may be inf: too few photos, every disease possible
    Column("monitor_coverage", Float),
    Column("monitor_set_size", Float),
    Column("monitor_answered", Float),
    Column("note", Text),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def database_url(db_path: Path | None = None) -> str:
    if db_path is not None:
        return f"sqlite:///{Path(db_path).as_posix()}"
    url = os.environ.get("DATABASE_URL")
    if url:
        # Supabase gives "postgresql://..." or "postgres://..."; SQLAlchemy needs the driver name.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url
    return f"sqlite:///{DB_PATH.as_posix()}"   # DB_PATH looked up at call time, so tests can point it elsewhere


@lru_cache(maxsize=8)
def _engine(url: str):
    if url.startswith("sqlite:///"):
        Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
        eng = create_engine(url, connect_args={"check_same_thread": False})
    else:
        eng = create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2)
    meta.create_all(eng)
    return eng


@contextmanager
def connect(db_path: Path | None = None):
    with _engine(database_url(db_path)).begin() as con:   # one transaction, committed on success
        yield con


def save_image(data: bytes, suffix: str = ".jpg", images_dir: Path | None = None, db_path: Path | None = None) -> str:
    name = f"{uuid.uuid4().hex}{suffix}"
    if images_dir is not None:                # legacy: write a file (kept for old callers/tests)
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / name).write_bytes(data)
        return name
    with connect(db_path) as con:
        con.execute(insert(images_t).values(name=name, data=data))
    return name


def load_image(name: str, db_path: Path | None = None) -> bytes:
    with connect(db_path) as con:
        row = con.execute(select(images_t.c.data).where(images_t.c.name == name)).first()
    if row is None:
        raise FileNotFoundError(name)
    return bytes(row[0])


def case_status(assessment: dict) -> str:
    return {"expert": "pending", "retake": "retake"}.get(assessment["status"], "answered")


def create_case(session_id: str, crop: str, image_path: str, assessment: dict, db_path: Path | None = None,
                audit: bool = False) -> int:
    """audit=True: the assistant answered, but this photo is ALSO randomly sent to an expert for checking.
    Random audits are an unbiased sample of what farmers send, so only they may recalibrate the conformal
    threshold (photos the assistant itself sent to experts are the hard ones, a biased sample)."""
    with connect(db_path) as con:
        res = con.execute(insert(cases).values(
            created_at=now(), session_id=session_id, crop=crop, image_path=image_path, seed=assessment["seed"],
            status=case_status(assessment), model_label=assessment.get("label"),
            probability=assessment.get("probability"), shortlist=json.dumps(assessment.get("shortlist", [])),
            assessment=json.dumps(assessment), audit=int(audit)))
        return int(res.inserted_primary_key[0])


def update_assessment(case_id: int, assessment: dict, db_path: Path | None = None) -> None:
    """After a follow-up answer or the extent question, the decision can change (an expert's answer can't)."""
    with connect(db_path) as con:
        current = con.execute(select(cases.c.status).where(cases.c.id == case_id)).scalar_one()
        status = current if current == "expert_answered" else case_status(assessment)
        con.execute(update(cases).where(cases.c.id == case_id).values(
            status=status, model_label=assessment.get("label"), probability=assessment.get("probability"),
            shortlist=json.dumps(assessment.get("shortlist", [])), assessment=json.dumps(assessment)))


def add_message(case_id: int, role: str, text: str, meta: dict | None = None, db_path: Path | None = None) -> None:
    with connect(db_path) as con:
        con.execute(insert(messages_t).values(case_id=case_id, created_at=now(), role=role, text=text,
                                              meta=json.dumps(meta or {})))


def messages(case_id: int, db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        rows = con.execute(select(messages_t).where(messages_t.c.case_id == case_id).order_by(messages_t.c.id))
        return [dict(r._mapping) | {"meta": json.loads(r.meta or "{}")} for r in rows]


def get_case(case_id: int, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as con:
        row = con.execute(select(cases).where(cases.c.id == case_id)).first()
    return _row(row) if row else None


def list_cases(status: str | None = None, db_path: Path | None = None) -> list[dict]:
    q = select(cases).order_by(cases.c.id)
    if status:
        q = q.where(cases.c.status == status)
    with connect(db_path) as con:
        return [_row(r) for r in con.execute(q)]


def expert_queue(db_path: Path | None = None) -> list[dict]:
    """Cases waiting for an expert: those the assistant sent, plus random audits not yet checked."""
    q = (select(cases).where(cases.c.expert_label.is_(None))
         .where((cases.c.status == "pending") | ((cases.c.audit == 1) & (cases.c.status == "answered")))
         .order_by(cases.c.id))
    with connect(db_path) as con:
        return [_row(r) for r in con.execute(q)]


def expert_answer(case_id: int, label: str, note: str, db_path: Path | None = None) -> None:
    """Expert labels a case. The label goes to the retraining pool (and, for random audits, recalibration)."""
    with connect(db_path) as con:
        con.execute(update(cases).where(cases.c.id == case_id).values(
            status="expert_answered", expert_label=label, expert_note=note, answered_at=now()))


# ---------- live calibration storage ----------

def clear_calibration_points(db_path: Path | None = None) -> None:
    with connect(db_path) as con:
        con.execute(delete(points_t))


def add_calibration_points(rows: list[tuple[str, int | None, int, list[float]]], db_path: Path | None = None) -> None:
    """rows: (source, case_id, label_idx, logits). -inf logits (other crop) are stored as null."""
    if not rows:
        return
    with connect(db_path) as con:
        con.execute(insert(points_t), [
            {"created_at": now(), "source": s, "case_id": c, "label_idx": int(y),
             "logits": json.dumps([None if v == float("-inf") else float(v) for v in lg])} for s, c, y, lg in rows])


def calibration_points(db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        rows = con.execute(select(points_t).order_by(points_t.c.id)).all()
    out = []
    for r in rows:
        d = dict(r._mapping)
        d["logits"] = [float("-inf") if v is None else v for v in json.loads(d["logits"])]
        out.append(d)
    return out


def add_calibration_run(run: dict, db_path: Path | None = None) -> None:
    keys = ("n_points", "n_field_points", "temperature", "qhat", "monitor_coverage", "monitor_set_size",
            "monitor_answered", "note")
    with connect(db_path) as con:
        con.execute(insert(runs_t).values(created_at=now(), **{k: run.get(k) for k in keys}))


def calibration_runs(db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        return [dict(r._mapping) for r in con.execute(select(runs_t).order_by(runs_t.c.id))]


def _row(r) -> dict:
    d = dict(r._mapping)
    d["shortlist"] = json.loads(d["shortlist"] or "[]")
    d["assessment"] = json.loads(d["assessment"])
    return d
