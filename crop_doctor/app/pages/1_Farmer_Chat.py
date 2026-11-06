"""Farmer chat: send a leaf photo, get an honest answer (or an expert), ask follow-up questions."""
from __future__ import annotations

import io
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # project root, so `crop_doctor` imports work

import streamlit as st  # noqa: E402
from PIL import Image  # noqa: E402

from crop_doctor.app import db  # noqa: E402
import random  # noqa: E402

from crop_doctor.app.ui import SAMPLES_DIR, calibrated_doctor, diagnosis_card, llm_enabled, samples  # noqa: E402
from crop_doctor.assistant import llm  # noqa: E402
from crop_doctor.assistant.decision import knowledge  # noqa: E402

st.set_page_config(page_title="Crop Doctor: Farmer Chat", layout="centered")
ss = st.session_state
ss.setdefault("session_id", uuid.uuid4().hex[:12])
ss.setdefault("case_id", None)

CAPTURE_GUIDE = """**How to take a good photo**
- One affected leaf, filling most of the photo
- In daylight, without flash, and not in strong sun glare
- Hold the phone steady and tap the leaf on the screen to focus
- Optional: a second photo of the whole plant"""


# ---------- actions ----------

def start_case(img_bytes: bytes, crop: str, seed: int | None = None) -> None:
    img = Image.open(io.BytesIO(img_bytes))
    a = calibrated_doctor().assess(img, crop, seed=seed)
    name = db.save_image(img_bytes)
    # Random audit: some photos the assistant answers are ALSO checked by an expert. Chosen at random, so
    # they are a fair sample: the only expert labels allowed to recalibrate the assistant.
    audit = a["status"] in ("diagnosis", "healthy") and random.random() < ss.get("audit_rate", db.AUDIT_RATE)
    cid = db.create_case(ss.session_id, crop, name, a, audit=audit)
    db.add_message(cid, "farmer", f"[photo of a {crop} leaf]", {"image": name})
    ss.case_id, ss.answers = cid, {}
    post_reply(cid, a)
    if audit:
        db.add_message(cid, "assistant", "An expert will also double-check this answer (we check some answers at "
                       "random to keep the assistant honest). You'll see their reply here.", {"status": "audit"})


def post_reply(cid: int, a: dict, question: str | None = None) -> None:
    history = [{"role": "user" if m["role"] == "farmer" else "assistant",
                "content": m["text"] if m["role"] != "expert" else f"Expert said: {m['text']}"}
               for m in db.messages(cid)[-6:]]
    with st.spinner("Writing a reply ..."):
        r = llm.reply(a, question=question, history=history if question else None, language=ss.get("language", "English"))
    db.add_message(cid, "assistant", r.text, {"sources": r.sources, "used_llm": r.used_llm,
                                              "fallback": r.fallback_reason, "status": a["status"]})


def reassess(cid: int, **kwargs) -> dict:
    case = db.get_case(cid)
    prev = case["assessment"]
    img = Image.open(db.IMAGES / case["image_path"])
    a = calibrated_doctor().assess(img, case["crop"], seed=case["seed"],
                        question_id=kwargs.get("question_id", ss.answers.get("question_id")),
                        option=kwargs.get("option", ss.answers.get("option")),
                        extent=kwargs.get("extent", prev.get("_extent")))
    a["_extent"] = kwargs.get("extent", prev.get("_extent"))
    db.update_assessment(cid, a)
    return a


def answer_question(cid: int, qid: str, option: int | None, text: str) -> None:
    db.add_message(cid, "farmer", text)
    if option is None:                                  # "Not sure": send to expert
        a = db.get_case(cid)["assessment"] | {"status": "expert", "reason": "the farmer wasn't sure"}
        a["message"] = "No problem. I've sent your photo to an expert, who will reply soon."
        db.update_assessment(cid, a)
    else:
        ss.answers = {"question_id": qid, "option": option}
        a = reassess(cid, question_id=qid, option=option)
    post_reply(cid, a)


def answer_extent(cid: int, value: str, text: str) -> None:
    db.add_message(cid, "farmer", text)
    a = reassess(cid, extent=value)
    u = a["urgency"]
    db.add_message(cid, "assistant", f"Thanks. Act within **{u['act_within']}**. {u['why']}", {"status": a["status"]})


# ---------- sidebar ----------

with st.sidebar:
    st.header("Crop Doctor")
    st.selectbox("Reply language", ["English", "Hindi", "Tamil", "Telugu", "Marathi"], key="language",
                 help="Needs the AI reply (API key). Template replies are in English.")
    if st.button("New photo", use_container_width=True):
        ss.case_id = None
        st.rerun()
    st.caption("AI replies: " + ("on" if llm_enabled() else "off (no API key): sourced template replies"))
    with st.expander("Demo settings"):
        st.slider("Random audit rate", 0.0, 1.0, db.AUDIT_RATE, 0.05, key="audit_rate",
                  help="Share of answered photos also sent to an expert. Set to 1.0 to demo the audit loop.")

st.title("Farmer chat")

# ---------- no case yet: get a photo ----------

if ss.case_id is None:
    # On the main page, not the sidebar: on phones the sidebar is hidden, and the crop matters for accuracy.
    crop = st.radio("Which crop is this?", ["tomato", "potato"], horizontal=True, key="crop")
    st.info(CAPTURE_GUIDE)
    tab_up, tab_cam, tab_sample = st.tabs(["Upload photo", "Take photo", "Try a sample"])
    with tab_cam:
        # Opt-in: the browser only asks for camera permission when the farmer turns it on.
        if st.toggle("Turn on camera"):
            shot = st.camera_input("Take a photo of one leaf")
            if shot is not None:
                start_case(shot.getvalue(), crop)
                st.rerun()
    with tab_up:
        up = st.file_uploader("Choose a leaf photo", type=["jpg", "jpeg", "png", "webp"])
        if up is not None and st.button("Check this photo", type="primary"):
            start_case(up.getvalue(), crop)
            st.rerun()
    with tab_sample:
        options = {s["title"]: s for s in samples()}
        pick = st.selectbox("Demo photos (real field photos the model never saw)", list(options))
        s = options[pick]
        st.image(str(SAMPLES_DIR / s["file"]), width=260, caption=f"Crop: {s['crop']}")
        if st.button("Use this sample", type="primary"):
            start_case((SAMPLES_DIR / s["file"]).read_bytes(), s["crop"], seed=s["seed"])
            st.rerun()
    st.stop()

# ---------- the conversation ----------

cid = ss.case_id
case = db.get_case(cid)
a = case["assessment"]
msgs = db.messages(cid)
for i, m in enumerate(msgs):
    role = {"farmer": "user", "assistant": "assistant", "expert": "assistant"}[m["role"]]
    with st.chat_message(role, avatar="🧑‍🌾" if m["role"] == "expert" else None):
        if m["meta"].get("image"):
            st.image(str(db.IMAGES / m["meta"]["image"]), width=260)
        else:
            st.markdown(("**Expert:** " if m["role"] == "expert" else "") + m["text"])
        if m["role"] == "assistant" and m["meta"].get("sources"):
            with st.expander("Sources"):
                for src in m["meta"]["sources"]:
                    st.markdown(f"- {src}")

diagnosis_card(a)

# ---------- what the farmer can do next ----------

status = case["status"]
if a["status"] == "question" and status != "expert_answered":
    q = a["question"]
    st.markdown(f"**{q['question']}**")
    for j, o in enumerate(q["options"]):
        st.button(o["text"], key=f"opt{j}", on_click=answer_question, args=(cid, q["id"], j, o["text"]),
                  use_container_width=True)
    st.button("I'm not sure", key="opt_none", on_click=answer_question, args=(cid, q["id"], None, "I'm not sure"),
              use_container_width=True)
elif a["status"] == "diagnosis" and not a.get("_extent"):
    eq = knowledge()["extent_question"]
    st.markdown(f"**{eq['question']}**")
    cols = st.columns(len(eq["options"]))
    for col, o in zip(cols, eq["options"]):
        col.button(o["text"], key=f"ext_{o['value']}", on_click=answer_extent, args=(cid, o["value"], o["text"]),
                   use_container_width=True)
elif status == "pending":
    st.info("Waiting for an expert. You can keep this page open or come back later.")
    if st.button("Check for expert reply"):
        st.rerun()
elif a["status"] == "retake":
    if st.button("Send a new photo", type="primary"):
        ss.case_id = None
        st.rerun()

if a["status"] != "retake":
    text = st.chat_input("Ask a question about this disease ...")
    if text:
        db.add_message(cid, "farmer", text)
        post_reply(cid, db.get_case(cid)["assessment"], question=text)
        st.rerun()
