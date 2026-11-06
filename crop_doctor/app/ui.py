"""Shared helpers for the Streamlit pages: cached model, small display pieces."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:          # streamlit runs pages as scripts; make `crop_doctor` importable
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from crop_doctor.assistant.decision import disease_name  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
URGENCY_STYLE = {"urgent": ("error", "Urgent"), "soon": ("warning", "Soon"), "routine": ("info", "Routine")}


@st.cache_resource(show_spinner="Loading the crop disease model ...")
def doctor():
    from crop_doctor.assistant.pipeline import CropDoctor
    return CropDoctor(alpha=0.1)


def calibrated_doctor():
    """The cached model with the LATEST live calibration applied (an expert may have just added labels)."""
    from crop_doctor.app import db
    from crop_doctor.assistant import live_calibration as lc
    doc = doctor()
    runs = db.calibration_runs()
    if not runs or not db.calibration_points():
        with st.spinner("First start: calibrating on field photos ..."):
            lc.ensure_initialised(doc)
    else:
        doc.set_calibration(runs[-1]["temperature"], runs[-1]["qhat"])
    return doc


@st.cache_resource(show_spinner="Loading the treatment notes ...")
def retriever():
    from crop_doctor.knowledge.rag import default_retriever
    return default_retriever()


def samples() -> list[dict]:
    return json.loads((SAMPLES_DIR / "samples.json").read_text())


def llm_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def diagnosis_card(a: dict) -> None:
    """The coloured result box shown under the assistant's reply."""
    with st.container(border=True):
        status = a["status"]
        if status in ("diagnosis", "healthy"):
            st.markdown(f"**Most likely: {disease_name(a['label'])}**  ·  {a['probability']:.0%} likely")
            if status == "diagnosis":
                u = a["urgency"]
                kind, word = URGENCY_STYLE[u["level"]]
                getattr(st, kind)(f"**{word}: act within {u['act_within']}.** {u['why']}")
                sev = a.get("severity_estimate", {})
                if sev.get("fraction") is not None:
                    st.caption(f"Damaged leaf area in this photo: about {sev['fraction']:.0%} "
                               "(rough colour-based estimate, not used for the diagnosis)")
                st.caption("Not certain: please confirm with a local expert (KVK / agriculture officer) before spraying.")
        elif status in ("question", "expert"):
            names = [disease_name(c) for c in a["shortlist"]]
            label = "Possible diseases" if names else "No disease matched well"
            st.markdown(f"**{label}:** " + (", ".join(names) if names else "-"))
            for t in a["top"][:3]:
                st.progress(min(t["probability"], 1.0), text=f"{t['name']}: {t['probability']:.0%}")
        elif status == "retake":
            st.warning("Photo not usable. " + a["message"])
