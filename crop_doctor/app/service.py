"""Everything the farmer and the expert can DO, as plain functions. Used by both front ends:
the Streamlit app (local demo) and the FastAPI server behind the Vercel website.

Keeping this in one place means the website and the Streamlit app can't drift apart.
"""
from __future__ import annotations

import io
import random

from PIL import Image

from crop_doctor.app import db
from crop_doctor.assistant import live_calibration as lc
from crop_doctor.assistant import llm
from crop_doctor.assistant.decision import disease_name, knowledge

AUDIT_NOTE = ("An expert will also double-check this answer (we check some answers at random to keep the "
              "assistant honest). You'll see their reply here.")


def ensure_calibrated(doctor) -> dict:
    """Apply the latest live calibration (an expert may have just added labels)."""
    runs = db.calibration_runs()
    if not runs or not db.calibration_points():
        return lc.ensure_initialised(doctor)
    doctor.set_calibration(runs[-1]["temperature"], db.run_qhat(runs[-1]))
    return runs[-1]


def _history(cid: int) -> list[dict]:
    return [{"role": "user" if m["role"] == "farmer" else "assistant",
             "content": m["text"] if m["role"] != "expert" else f"Expert said: {m['text']}"}
            for m in db.messages(cid)[-6:]]


def post_reply(cid: int, a: dict, question: str | None = None, language: str = "English") -> None:
    r = llm.reply(a, question=question, history=_history(cid) if question else None, language=language)
    db.add_message(cid, "assistant", r.text, {"sources": r.sources, "used_llm": r.used_llm,
                                              "fallback": r.fallback_reason, "status": a["status"]})


def start_case(doctor, img_bytes: bytes, crop: str, session_id: str, *, seed: int | None = None,
               audit_rate: float = db.AUDIT_RATE, language: str = "English", rng: random.Random | None = None) -> int:
    ensure_calibrated(doctor)
    img = Image.open(io.BytesIO(img_bytes))
    a = doctor.assess(img, crop, seed=seed)
    name = db.save_image(img_bytes)
    # Random audit: some photos the assistant answers are ALSO checked by an expert. Chosen at random, so they
    # are a fair sample: the only expert labels allowed to recalibrate the assistant.
    audit = a["status"] in ("diagnosis", "healthy") and (rng or random).random() < audit_rate
    cid = db.create_case(session_id, crop, name, a, audit=audit)
    db.add_message(cid, "farmer", f"[photo of a {crop} leaf]", {"image": name})
    post_reply(cid, a, language=language)
    if audit:
        db.add_message(cid, "assistant", AUDIT_NOTE, {"status": "audit"})
    return cid


def reassess(doctor, cid: int, *, question_id: str | None = None, option: int | None = None,
             extent: str | None = None) -> dict:
    case = db.get_case(cid)
    prev = case["assessment"]
    q_id = question_id or prev.get("_question_id")
    opt = option if option is not None else prev.get("_option")
    ext = extent or prev.get("_extent")
    ensure_calibrated(doctor)
    a = doctor.assess(Image.open(io.BytesIO(db.load_image(case["image_path"]))), case["crop"], seed=case["seed"],
                      question_id=q_id, option=opt, extent=ext)
    a.update({"_question_id": q_id, "_option": opt, "_extent": ext})
    db.update_assessment(cid, a)
    return a


def answer_question(doctor, cid: int, option: int | None, language: str = "English") -> dict:
    """option = index of the farmer's choice, or None for "I'm not sure" (-> expert)."""
    case = db.get_case(cid)
    q = case["assessment"]["question"]
    db.add_message(cid, "farmer", "I'm not sure" if option is None else q["options"][option]["text"])
    if option is None:
        a = case["assessment"] | {"status": "expert", "reason": "the farmer wasn't sure",
                                  "message": "No problem. I've sent your photo to an expert, who will reply soon."}
        db.update_assessment(cid, a)
    else:
        a = reassess(doctor, cid, question_id=q["id"], option=option)
    post_reply(cid, a, language=language)
    return a


def answer_extent(doctor, cid: int, value: str) -> dict:
    opt = next(o for o in knowledge()["extent_question"]["options"] if o["value"] == value)
    db.add_message(cid, "farmer", opt["text"])
    a = reassess(doctor, cid, extent=value)
    u = a["urgency"]
    db.add_message(cid, "assistant", f"Thanks. Act within **{u['act_within']}**. {u['why']}", {"status": a["status"]})
    return a


def ask(cid: int, text: str, language: str = "English") -> None:
    db.add_message(cid, "farmer", text)
    post_reply(cid, db.get_case(cid)["assessment"], question=text, language=language)


def expert_answer(doctor, cid: int, label: str, note: str) -> dict | None:
    """Store the expert's answer, show it to the farmer; random audits also recalibrate the assistant."""
    case = db.get_case(cid)
    db.expert_answer(cid, label, note)
    verdict = disease_name(label) if label in doctor.classes else label
    db.add_message(cid, "expert", f"{verdict}. {note}".strip())
    return lc.add_expert_label(doctor, case, label)
