"""Crop Doctor API: the backend of the website (deployed on Render).

    uvicorn server.main:app --reload            # local, http://localhost:8000/docs

It reuses the exact same pipeline as the Streamlit app (crop_doctor/app/service.py). On Render it runs the
ONNX model on CPU (no PyTorch) and stores cases in Supabase Postgres (DATABASE_URL).

Environment variables:
  DATABASE_URL              Postgres connection string (Supabase). Unset = local SQLite file.
  EXPERT_KEY                password for the expert dashboard endpoints. Unset = open (local dev only).
  ALLOWED_ORIGINS           comma-separated website origins allowed to call the API (CORS), e.g. the Vercel URL.
  ANTHROPIC_API_KEY         optional: friendly AI replies; without it, sourced template replies.
  CROP_DOCTOR_APP_CONFIG    model/calibration config (server/assets/app_model.json on Render).
  CROP_DOCTOR_LOGITS_DIR    cached model outputs for live calibration (server/assets/logits on Render).
"""
from __future__ import annotations

import hmac
import io
import json
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from crop_doctor import config
from crop_doctor.app import db, service
from crop_doctor.assistant import live_calibration as lc
from crop_doctor.assistant.decision import disease_name, knowledge
from crop_doctor.assistant.llm import llm_available

SAMPLES_DIR = config.ROOT / "crop_doctor" / "app" / "samples"
METRICS_DIR = config.OUTPUTS_DIR / "metrics"
MAX_UPLOAD = 10 * 1024 * 1024
LANGUAGES = ["English", "Hindi", "Tamil", "Telugu", "Marathi", "Kannada", "Bengali", "Punjabi"]
STATE: dict = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from crop_doctor.assistant.pipeline import CropDoctor
    from crop_doctor.knowledge.rag import default_retriever
    STATE["doctor"] = CropDoctor(alpha=0.1)
    from crop_doctor.assistant import live_calibration
    live_calibration.ensure_initialised(STATE["doctor"])     # also resets calibration if the model was updated
    default_retriever()                                        # load embeddings now, not on the first question
    yield


app = FastAPI(title="Crop Doctor API", version="2.0", lifespan=lifespan)
origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"],
                   allow_origin_regex=os.environ.get("ALLOWED_ORIGIN_REGEX"))


def doctor():
    return STATE["doctor"]


def require_expert(x_expert_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("EXPERT_KEY")
    if expected and not (x_expert_key and hmac.compare_digest(x_expert_key, expected)):
        raise HTTPException(401, "Expert key required")


# ---------- views ----------

def disease_view(label: str | None) -> dict | None:
    if not label:
        return None
    d = knowledge()["diseases"].get(label)
    return {"label": label, "name": disease_name(label) if d else label, "crop": d["crop"] if d else None}


def assessment_view(a: dict) -> dict:
    keep = ("status", "crop", "probability", "via", "reason", "message", "urgency", "severity_estimate", "quality",
            "after_answer")
    out = {k: a.get(k) for k in keep if k in a}
    out["disease"] = disease_view(a.get("label"))
    out["shortlist"] = [disease_view(c) for c in a.get("shortlist", [])]
    out["top"] = a.get("top", [])
    out["extent"] = a.get("_extent")
    if a.get("status") == "question":
        q = a["question"]
        out["question"] = {"id": q["id"], "text": q["question"], "options": [o["text"] for o in q["options"]]}
    return out


def case_view(case: dict) -> dict:
    msgs = []
    for m in db.messages(case["id"]):
        item = {"role": m["role"], "text": m["text"], "created_at": m["created_at"],
                "sources": m["meta"].get("sources", []), "used_llm": m["meta"].get("used_llm", False)}
        if m["meta"].get("image"):
            item["image"] = f"/api/images/{m['meta']['image']}"
        msgs.append(item)
    return {"id": case["id"], "crop": case["crop"], "status": case["status"], "audit": bool(case["audit"]),
            "created_at": case["created_at"], "image": f"/api/images/{case['image_path']}",
            "assessment": assessment_view(case["assessment"]), "messages": msgs,
            "expert": disease_view(case["expert_label"]) if case["expert_label"] else None,
            "ask_extent": case["assessment"].get("status") == "diagnosis" and not case["assessment"].get("_extent")}


def get_case_or_404(cid: int) -> dict:
    case = db.get_case(cid)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


# ---------- public ----------

@app.get("/api/health")
def health():
    return {"ok": True, "model_loaded": "doctor" in STATE}


@app.get("/api/meta")
def meta():
    k = knowledge()
    samples = json.loads((SAMPLES_DIR / "samples.json").read_text())
    results = {}
    for name in ("exp1_shift", "exp5_final_model", "exp6_pipeline", "exp8_final_v2"):
        p = METRICS_DIR / f"{name}.json"
        if p.exists():
            results[name] = json.loads(p.read_text())
    return {
        "crops": doctor().crops,
        "diseases": [disease_view(c) for c in doctor().classes],
        "extent_question": {"text": k["extent_question"]["question"], "options": k["extent_question"]["options"]},
        "samples": [{"file": s["file"], "title": s["title"], "crop": s["crop"]} for s in samples],
        "languages": LANGUAGES,
        "llm_enabled": llm_available(),
        "expert_key_required": bool(os.environ.get("EXPERT_KEY")),
        "results": results,
    }


@app.get("/api/samples/{file}")
def sample_image(file: str):
    p = (SAMPLES_DIR / file).resolve()
    if p.parent != SAMPLES_DIR.resolve() or not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(404)
    return Response(p.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/images/{name}")
def image(name: str):
    try:
        data = db.load_image(name)
    except FileNotFoundError:
        raise HTTPException(404) from None
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@app.post("/api/cases")
async def create_case(crop: str = Form(...), file: UploadFile | None = File(default=None),
                      sample: str | None = Form(default=None), language: str = Form(default="English"),
                      x_session_id: str | None = Header(default=None)):
    if crop not in doctor().crops:
        raise HTTPException(400, f"crop must be one of {doctor().crops}")
    seed = None
    if sample:
        s = next((s for s in json.loads((SAMPLES_DIR / "samples.json").read_text()) if s["file"] == sample), None)
        if not s:
            raise HTTPException(404, "Unknown sample")
        data, seed, crop = (SAMPLES_DIR / s["file"]).read_bytes(), s["seed"], s["crop"]
    elif file is not None:
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Photo too large (max 10 MB)")
        try:
            Image.open(io.BytesIO(data)).verify()
        except (UnidentifiedImageError, OSError):
            raise HTTPException(400, "That file is not a photo we can read") from None
    else:
        raise HTTPException(400, "Send a photo or choose a sample")
    session = (x_session_id or secrets.token_hex(6))[:64]
    cid = service.start_case(doctor(), data, crop, session, seed=seed, language=language)
    return case_view(db.get_case(cid))


@app.get("/api/cases/{cid}")
def read_case(cid: int):
    return case_view(get_case_or_404(cid))


class QuestionAnswer(BaseModel):
    option: int | None = Field(default=None, description="index of the chosen option; null = I'm not sure")
    language: str = "English"


@app.post("/api/cases/{cid}/question")
def answer_question(cid: int, body: QuestionAnswer):
    case = get_case_or_404(cid)
    q = case["assessment"].get("question")
    if case["assessment"].get("status") != "question" or not q:
        raise HTTPException(409, "No question is waiting for an answer")
    if body.option is not None and not 0 <= body.option < len(q["options"]):
        raise HTTPException(400, "Unknown option")
    service.answer_question(doctor(), cid, body.option, language=body.language)
    return case_view(db.get_case(cid))


class Extent(BaseModel):
    value: str


@app.post("/api/cases/{cid}/extent")
def answer_extent(cid: int, body: Extent):
    case = get_case_or_404(cid)
    if case["assessment"].get("status") != "diagnosis":
        raise HTTPException(409, "Only for a diagnosis")
    if body.value not in [o["value"] for o in knowledge()["extent_question"]["options"]]:
        raise HTTPException(400, "Unknown value")
    service.answer_extent(doctor(), cid, body.value)
    return case_view(db.get_case(cid))


class Ask(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    language: str = "English"


@app.post("/api/cases/{cid}/messages")
def ask(cid: int, body: Ask):
    case = get_case_or_404(cid)
    if case["assessment"].get("status") == "retake":
        raise HTTPException(409, "Please send a new photo first")
    service.ask(cid, body.text.strip(), language=body.language)
    return case_view(db.get_case(cid))


# ---------- expert ----------

@app.get("/api/expert/queue", dependencies=[Depends(require_expert)])
def expert_queue():
    out = []
    for c in db.expert_queue():
        farmer = [m["text"] for m in db.messages(c["id"]) if m["role"] == "farmer" and not m["meta"].get("image")]
        out.append(case_view(c) | {"farmer_said": farmer, "kind": "audit" if c["audit"] and c["status"] == "answered"
                                   else "unsure", "model_guess": disease_view(c["model_label"]),
                                   "options": [disease_view(d) for d in doctor().classes
                                               if knowledge()["diseases"][d]["crop"] == c["crop"]]})
    return out


class ExpertAnswer(BaseModel):
    label: str
    note: str = Field(default="", max_length=2000)


@app.post("/api/expert/cases/{cid}", dependencies=[Depends(require_expert)])
def expert_answer(cid: int, body: ExpertAnswer):
    get_case_or_404(cid)
    run = service.expert_answer(doctor(), cid, body.label, body.note.strip())
    return {"recalibrated": run is not None, "run": run}


@app.get("/api/expert/trust", dependencies=[Depends(require_expert)])
def trust():
    runs = db.calibration_runs()
    resets = [i for i, r in enumerate(runs) if (r["note"] or "").startswith("reset")]
    since = runs[resets[-1]:] if resets else runs
    def clean(r):  # JSON has no "infinity": show it as null
        fix = lambda v: None if isinstance(v, float) and v == float("inf") else v  # noqa: E731
        return {k: ({kk: fix(vv) for kk, vv in v.items()} if isinstance(v, dict) else fix(v)) for k, v in r.items()}
    return {"current": clean(runs[-1]) if runs else None, "since_reset": [clean(r) for r in since],
            "all": [clean(r) for r in runs[-200:]]}


class CalibrationAction(BaseModel):
    action: str = Field(pattern="^(reset_lab|reset_field|simulate)$")
    k: int = Field(default=10, ge=1, le=50)


@app.post("/api/expert/calibration", dependencies=[Depends(require_expert)])
def calibration(body: CalibrationAction):
    d = doctor()
    if body.action == "reset_lab":
        run = lc.reset(d, "lab")
    elif body.action == "reset_field":
        run = lc.reset(d, "field")
    else:
        run = lc.simulate_expert_labels(d, body.k, seed=len(db.calibration_runs()))
    return trust() | {"last_action": body.action, "run_qhat_finite": run["qhat"] != float("inf")}


@app.get("/api/expert/answered", dependencies=[Depends(require_expert)])
def answered():
    done = [c for c in db.list_cases() if c["expert_label"]]
    rows = [{"id": c["id"], "crop": c["crop"], "audit": bool(c["audit"]), "assistant": disease_view(c["model_label"]),
             "expert": disease_view(c["expert_label"]), "agree": c["model_label"] == c["expert_label"],
             "answered_at": c["answered_at"]} for c in done]
    audits = [r for r in rows if r["audit"]]
    return {"cases": rows[::-1], "retraining_pool": len(rows), "audits": len(audits),
            "audit_accuracy": (sum(r["agree"] for r in audits) / len(audits)) if audits else None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

