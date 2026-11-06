"""Crop Doctor: Streamlit entry page.

    streamlit run crop_doctor/app/Home.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root, so `crop_doctor` imports work

import streamlit as st  # noqa: E402

from crop_doctor import config  # noqa: E402

st.set_page_config(page_title="Crop Doctor", layout="centered")
st.title("Crop Doctor")
st.markdown("#### A crop disease assistant that knows when it doesn't know")
st.markdown(
    "Send a photo of a tomato or potato leaf. If the assistant is sure, it tells you the most likely disease, "
    "how urgent it is and what to do, with sources. If it isn't sure, it asks one question or sends your photo "
    "to an expert instead of guessing."
)

c1, c2 = st.columns(2)
c1.page_link("pages/1_Farmer_Chat.py", label="Farmer chat", icon=":material/chat:")
try:
    c2.page_link("pages/2_Expert_Dashboard.py", label="Expert dashboard", icon=":material/verified_user:")
except Exception:  # noqa: BLE001 - dashboard is added on Day 8
    c2.caption("Expert dashboard: coming next")

metrics = config.OUTPUTS_DIR / "metrics"
try:
    e1 = json.loads((metrics / "exp1_shift.json").read_text())["results"]
    e5 = json.loads((metrics / "exp5_final_model.json").read_text())["results"]["final_model"]
    e6 = json.loads((metrics / "exp6_pipeline.json").read_text())["assistant_on_field_test"]["typical"]
    st.divider()
    st.markdown("##### Results on real field photos the models never saw")
    a, b, c, d = st.columns(4)
    a.metric("Lab-only model", f"{e1['field_test']['accuracy']:.0%}", help="accuracy on field photos, while 83% confident")
    b.metric("Final model", f"{e5['accuracy']:.0%}", help="crop-aware ConvNeXt-Tiny, top-1 accuracy")
    c.metric("Answered by assistant", f"{e6['answered_by_assistant']:.0%}", help="the rest go to an expert")
    d.metric("Correct when answering", f"{e6['accuracy_when_answered']:.0%}", help="simulated farmers answer follow-up questions")
except FileNotFoundError:
    st.caption("Run the experiments to show results here.")
