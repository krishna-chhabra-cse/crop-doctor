"""Expert dashboard: answer farmers' unclear photos, check random audits, watch the trust meter."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # project root, so `crop_doctor` imports work

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from crop_doctor.app import db, service  # noqa: E402
from crop_doctor.app.ui import calibrated_doctor  # noqa: E402
from crop_doctor.assistant import live_calibration as lc  # noqa: E402
from crop_doctor.assistant.decision import disease_name, knowledge  # noqa: E402

st.set_page_config(page_title="Crop Doctor: Expert Dashboard", layout="wide")
doc = calibrated_doctor()
OTHER, UNUSABLE = "Other disease / not in the list", "Photo unusable"


def submit(case: dict, choice: str, note: str) -> None:
    label = next((c for c in doc.classes if disease_name(c) == choice), choice)
    run = service.expert_answer(doc, case["id"], label, note)
    if run:
        st.toast(f"Random audit added to calibration: monitor coverage now {run['monitor_coverage']:.0%}, "
                 f"avg shortlist {run['monitor_set_size']:.1f}")
    else:
        st.toast("Answer sent to the farmer. Label saved to the retraining pool.")


st.title("Expert dashboard")
st.caption("Demo version: no login. A real deployment needs expert accounts and access control.")
queue = db.expert_queue()
tab_q, tab_meter, tab_done = st.tabs([f"Queue ({len(queue)})", "Trust meter", "Answered"])

# ---------- queue ----------
with tab_q:
    if not queue:
        st.info("No photos waiting. Send an unclear photo from the farmer chat to see it here.")
    for case in queue:
        a = case["assessment"]
        with st.container(border=True):
            left, right = st.columns([1, 2])
            left.image(db.load_image(case["image_path"]), use_container_width=True)
            with right:
                kind = ("**Random audit:** the assistant answered *" + disease_name(case["model_label"]) +
                        f"* ({case['probability']:.0%}). Please check it." if case["audit"] and case["model_label"]
                        else f"**Sent by the assistant:** {a.get('reason', 'unsure')}.")
                st.markdown(f"Case #{case['id']} · {case['crop']} · {case['created_at'][:16].replace('T', ' ')}")
                st.markdown(kind)
                st.markdown("Model's top guesses: " + ", ".join(f"{t['name']} {t['probability']:.0%}" for t in a["top"]))
                farmer_text = [m["text"] for m in db.messages(case["id"]) if m["role"] == "farmer" and not m["meta"].get("image")]
                if farmer_text:
                    st.markdown("Farmer said: " + " · ".join(f"*{t}*" for t in farmer_text))
                crop_classes = [c for c in doc.classes if knowledge()["diseases"][c]["crop"] == case["crop"]]
                options = [disease_name(c) for c in crop_classes] + [OTHER, UNUSABLE]
                default = options.index(disease_name(case["model_label"])) if case["model_label"] in crop_classes else 0
                with st.form(key=f"form{case['id']}"):
                    choice = st.selectbox("Your diagnosis", options, index=default)
                    note = st.text_area("Advice for the farmer", placeholder="e.g. Remove the lower leaves and spray copper "
                                        "this week. Check again in 5 days.")
                    if st.form_submit_button("Send answer to farmer", type="primary"):
                        submit(case, choice, note)
                        st.rerun()

# ---------- trust meter ----------
with tab_meter:
    runs = pd.DataFrame(db.calibration_runs())
    last = runs.iloc[-1]
    st.markdown("Every random-audit label from an expert **recalibrates the assistant immediately** (temperature + "
                "conformal threshold). The model itself isn't retrained here. The chart shows how the current "
                "settings perform on a fixed monitor set of field photos (field_test, never used for fitting).")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Field labels in calibration", int(last["n_field_points"]))
    c2.metric("Shortlist contains the right disease", f"{last['monitor_coverage']:.0%}", help="target 90%")
    c3.metric("Avg. diseases in shortlist", f"{last['monitor_set_size']:.1f}")
    c4.metric("Answered without expert", f"{last['monitor_answered']:.0%}")
    if last["n_field_points"] == 0:
        st.warning("Calibrated on LAB photos only: the 90% promise is not valid for farm photos.")
    elif last["n_field_points"] < 9:
        st.warning("Fewer than 9 field labels: no safe threshold yet, so every disease stays possible.")

    resets = runs.index[runs["note"].fillna("").str.startswith("reset")]
    since = runs.iloc[resets.max() if len(resets) else 0:]
    chart = since.assign(**{"Coverage": since["monitor_coverage"], "Target (90%)": 0.9,
                            "Answered alone": since["monitor_answered"]})
    chart["Field labels"] = since["n_field_points"]
    st.markdown("**Since the last reset**")
    # Same colours as the report figures: aqua = coverage, grey = target, blue = answered alone.
    st.line_chart(chart.set_index("Field labels")[["Coverage", "Target (90%)", "Answered alone"]], height=260,
                  x_label="Field labels in calibration", y_label="Share of monitor photos",
                  color=["#1baf7a", "#8a8984", "#2a78d6"])
    st.line_chart(chart.set_index("Field labels")[["monitor_set_size"]].rename(columns={"monitor_set_size": "Avg. shortlist size"}),
                  height=200, x_label="Field labels in calibration", color=["#eb6834"])

    st.markdown("**Demo controls**: replay the Day 4 experiment live")
    b1, b2, b3 = st.columns(3)
    if b1.button("Reset: lab photos only", help="Shows the broken promise: coverage falls below the 90% it claims"):
        lc.reset(doc, "lab")
        st.rerun()
    if b2.button("Add 10 simulated expert labels", type="primary", help="10 labelled field photos not used for training"):
        lc.simulate_expert_labels(doc, 10, seed=len(runs))
        st.rerun()
    if b3.button("Reset: normal field calibration"):
        lc.reset(doc, "field")
        st.rerun()
    with st.expander("All recalibrations"):
        st.dataframe(runs[["created_at", "note", "n_points", "n_field_points", "temperature", "qhat",
                           "monitor_coverage", "monitor_set_size", "monitor_answered"]], hide_index=True)

# ---------- answered ----------
with tab_done:
    done = [c for c in db.list_cases() if c["expert_label"]]
    if not done:
        st.info("No expert answers yet.")
    else:
        df = pd.DataFrame([{"case": c["id"], "crop": c["crop"], "random audit": bool(c["audit"]),
                            "assistant said": disease_name(c["model_label"]) if c["model_label"] else "(sent to expert)",
                            "expert said": disease_name(c["expert_label"]) if c["expert_label"] in doc.classes else c["expert_label"],
                            "agree": c["model_label"] == c["expert_label"]} for c in done])
        audits = df[df["random audit"]]
        c1, c2 = st.columns(2)
        c1.metric("Labels in the retraining pool", len(df), help="all expert labels; used in the next periodic retraining")
        if len(audits):
            c2.metric("Assistant accuracy on random audits", f"{audits['agree'].mean():.0%}", help=f"{len(audits)} audits: an "
                      "unbiased live estimate, because audits are chosen at random")
        st.dataframe(df, hide_index=True)
