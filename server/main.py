"""Crop Doctor API: the backend of the website (deployed on Render).

    uvicorn server.main:app --reload            # local, http://localhost:8000/docs

It reuses the exact same pipeline as the Streamlit app (crop_doctor/app/service.py). On Render it runs the
ONNX model on CPU (no PyTorch) and stores cases in Supabase Postgres (DATABASE_URL).

Environment variables:
  DATABASE_URL              Postgres connection string (Supabase). Unset = local SQLite file.
  EXPERT_KEY                password for the expert dashboard endpoints. Unset = open (local dev only).
  ALLOWED_ORIGINS           comma-separated website origins allowed to call the API (CORS), e.g. the Vercel URL.
  GEMINI_API_KEY            optional: AI replies with Gemini (GEMINI_MODEL, default gemini-3.6-flash).
  ANTHROPIC_API_KEY         optional: AI replies with Claude. Neither key = sourced template replies.
  CROP_DOCTOR_APP_CONFIG    model/calibration config (server/assets/app_model.json on Render).
  CROP_DOCTOR_LOGITS_DIR    cached model outputs for live calibration (server/assets/logits on Render).
"""
from __future__ import annotations

import hmac
import io
import json
import logging
import os
import secrets
import time
import warnings
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from crop_doctor import config
from crop_doctor.app import db, service
from crop_doctor.assistant import live_calibration as lc
from crop_doctor.assistant.decision import disease_name, knowledge
from crop_doctor.assistant.llm import llm_available
from crop_doctor.assistant.llm import provider as llm_provider

SAMPLES_DIR = config.ROOT / "crop_doctor" / "app" / "samples"
METRICS_DIR = config.OUTPUTS_DIR / "metrics"
MAX_UPLOAD = 10 * 1024 * 1024
MAX_SIDE = 1600        # uploads are shrunk to this: the model sees 224 px, and the free server/database are small
MAX_PIXELS = 40_000_000  # bigger pictures are refused BEFORE decoding: a 0.5 MB PNG can unpack to 169 MP = ~2 GB of RAM
MAX_BODY = MAX_UPLOAD + 1024 * 1024    # the photo upload (POST /api/cases): photo + form fields
MAX_JSON = 64 * 1024                   # every other request: small JSON
log = logging.getLogger("crop_doctor")


def shrink_photo(data: bytes) -> bytes:
    """Upright (phone rotation tag applied) and at most MAX_SIDE px, re-saved as JPEG. A 12 MP phone photo
    otherwise costs ~100 MB of memory while it's checked, and ~5 MB in the database (free plan: 500 MB).
    Always re-saved, even when already small: that drops the EXIF block (GPS location, phone model) and
    anything hidden after the image data, so we never store or serve them."""
    with Image.open(io.BytesIO(data)) as im:
        k = min(1.0, MAX_SIDE / max(im.size))             # JPEG: decode at 1/2, 1/4 or 1/8 size straight away
        im.draft("RGB", (max(1, int(im.width * k)), max(1, int(im.height * k))))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=90)
        return out.getvalue()


def read_photo(data: bytes) -> bytes:
    """Check an uploaded file is a readable photo of sensible size, then shrink it. Anything wrong -> 400."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:      # reads the header only: size is known, nothing decoded
                if im.width * im.height > MAX_PIXELS:
                    raise HTTPException(400, "Photo too large (max 40 megapixels)")
                if min(im.size) < 32 or max(im.size) > 10 * min(im.size):   # a strip, not a leaf photo
                    raise HTTPException(400, "That doesn't look like a leaf photo (too small or too narrow)")
                im.verify()
            return shrink_photo(data)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - any decoding problem (truncated, bad checksum, bomb...) is the file's fault
        raise HTTPException(400, "That file is not a photo we can read") from None


class Guard:
    """Outer safety net (pure ASGI, runs before routing and auth, inside CORS so its replies carry CORS headers):
    - request bodies over the limit get 413 without being read into memory (by Content-Length, and by counting
      the bytes as they arrive when no length is given);
    - an unexpected error becomes a JSON 500 the website can show, instead of a reply without CORS headers that
      the browser reports as "Can't reach the server"."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = MAX_BODY if scope["path"] == "/api/cases" else MAX_JSON
        started = blocked = False
        received = 0

        async def guarded_send(message):
            nonlocal started
            if blocked:
                return                                    # we already answered 413: drop the app's own reply
            started = started or message["type"] == "http.response.start"
            await send(message)

        async def reply(status: int, detail: str):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, guarded_send)

        length = dict(scope["headers"]).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > limit):
            return await reply(413, "Request too large")

        async def counted_receive():
            nonlocal received, blocked
            message = await receive()
            if message["type"] == "http.request" and not blocked:
                received += len(message.get("body", b""))
                if received > limit:
                    if not started:
                        await reply(413, "Request too large")
                    blocked = True
            if blocked:
                return {"type": "http.disconnect"}        # the app stops reading; its reply is dropped
            return message

        try:
            await self.app(scope, counted_receive, guarded_send)
        except Exception:
            if blocked:
                return                                    # the app tripped over the cut-off body: 413 already sent
            log.exception("Unhandled error on %s %s", scope.get("method"), scope["path"])
            if started:
                raise
            await reply(500, "Something went wrong on the server. Please try again.")


def finite(value):
    """JSON has no "infinity" (an empty calibration gives q-hat = inf): show it as null, also inside dicts."""
    if isinstance(value, dict):
        return {k: finite(v) for k, v in value.items()}
    return None if isinstance(value, float) and value == float("inf") else value
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
app.add_middleware(Guard)               # added first = runs inside CORS, so its 413/500 replies get CORS headers
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"],
                   allow_origin_regex=os.environ.get("ALLOWED_ORIGIN_REGEX"))


def doctor():
    return STATE["doctor"]


def is_expert(x_expert_key: str | None) -> bool:
    expected = os.environ.get("EXPERT_KEY")
    return not expected or bool(x_expert_key and hmac.compare_digest(x_expert_key.encode(), expected.encode()))


def require_expert(x_expert_key: str | None = Header(default=None)) -> None:
    if not is_expert(x_expert_key):
        raise HTTPException(401, "Expert key required")


# Simple per-visitor rate limit (one server worker, so memory is enough). Protects the free server and the AI
# quota from scripts; far above what a farmer needs. Key = the visitor's IP address.
LIMITS = {"photo": (30, 600), "message": (60, 600)}          # (requests, seconds)
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def rate_limit(kind: str):
    def check(request: Request) -> None:
        if os.environ.get("CROP_DOCTOR_NO_RATE_LIMIT"):
            return
        # Cloudflare (in front of Render) sets CF-Connecting-IP and overwrites any client value; fall back to
        # X-Forwarded-For, then the socket address (local runs).
        ip = (request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
              or (request.client.host if request.client else "?")).split(",")[0].strip()
        limit, window = LIMITS[kind]
        q, now = _hits[(kind, ip)], time.monotonic()
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Too many requests. Please wait a few minutes and try again.")
        q.append(now)
    return check


def check_language(language: str) -> str:
    # The language goes into the AI prompt ("Reply in ..."), so only known values are accepted.
    if language not in LANGUAGES:
        raise HTTPException(400, f"language must be one of {LANGUAGES}")
    return language


# ---------- views ----------

def disease_view(label: str | None) -> dict | None:
    if not label:
        return None
    d = knowledge()["diseases"].get(label)
    if not d:
        return {"label": label, "name": label, "crop": None}
    # cause/spread/signs let the website explain the disease with pictures (fungus, bacteria, virus...).
    return {"label": label, "name": disease_name(label), "crop": d["crop"], "cause": d.get("cause"),
            "spread": d.get("spread"), "signs": d.get("key_signs")}


def assessment_view(a: dict) -> dict:
    keep = ("status", "crop", "probability", "via", "reason", "message", "urgency", "severity_estimate", "quality",
            "after_answer", "unfamiliar", "familiarity", "something_else")
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


def owned_case(cid: int, x_session_id: str | None = Header(default=None),
               x_expert_key: str | None = Header(default=None)) -> dict:
    """A farmer's case (photo + chat) is private: only the browser session that created it, or an expert, may
    read or change it. Case numbers count up, so without this anyone could read every farmer's photos.
    404 (not 403), so strangers can't even tell which case numbers exist."""
    case = get_case_or_404(cid)
    mine = bool(x_session_id) and hmac.compare_digest(x_session_id[:64].encode(), case["session_id"].encode())
    if not mine and not (
            os.environ.get("EXPERT_KEY") and is_expert(x_expert_key)):
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
        "llm_provider": llm_provider(),
        "expert_key_required": bool(os.environ.get("EXPERT_KEY")),
        "results": results,
    }


@app.get("/api/samples/{file}")
def sample_image(file: str):
    p = (SAMPLES_DIR / file).resolve()
    if p.parent != SAMPLES_DIR.resolve() or not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(404)
    media = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return Response(p.read_bytes(), media_type=media, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/images/{name}")
def image(name: str):
    try:
        data = db.load_image(name)
    except FileNotFoundError:
        raise HTTPException(404) from None
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@app.post("/api/cases", dependencies=[Depends(rate_limit("photo"))])
async def create_case(crop: str = Form(...), file: UploadFile | None = File(default=None),
                      sample: str | None = Form(default=None), language: str = Form(default="English"),
                      x_session_id: str | None = Header(default=None)):
    if crop not in doctor().crops:
        raise HTTPException(400, f"crop must be one of {doctor().crops}")
    check_language(language)
    seed = None
    if sample:
        s = next((s for s in json.loads((SAMPLES_DIR / "samples.json").read_text()) if s["file"] == sample), None)
        if not s:
            raise HTTPException(404, "Unknown sample")
        data, seed, crop = (SAMPLES_DIR / s["file"]).read_bytes(), s["seed"], s["crop"]
    elif file is not None:
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Photo too large (max 10 MB)")
        data = await run_in_threadpool(read_photo, data)
    else:
        raise HTTPException(400, "Send a photo or choose a sample")
    session = (x_session_id or secrets.token_hex(6))[:64]
    # The model and the AI reply (up to ~30-60 s) are slow, blocking work. Run them in a worker thread so the
    # server keeps answering other farmers and Render's health check meanwhile.
    cid = await run_in_threadpool(service.start_case, doctor(), data, crop, session, seed=seed, language=language)
    return case_view(await run_in_threadpool(db.get_case, cid))


@app.get("/api/cases/{cid}")
def read_case(case: dict = Depends(owned_case)):
    return case_view(case)


class QuestionAnswer(BaseModel):
    option: int | None = Field(default=None, description="index of the chosen option; null = I'm not sure")
    language: str = "English"


@app.post("/api/cases/{cid}/question", dependencies=[Depends(rate_limit("message"))])
def answer_question(cid: int, body: QuestionAnswer, case: dict = Depends(owned_case)):
    check_language(body.language)
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
def answer_extent(cid: int, body: Extent, case: dict = Depends(owned_case)):
    if case["assessment"].get("status") != "diagnosis":
        raise HTTPException(409, "Only for a diagnosis")
    if body.value not in [o["value"] for o in knowledge()["extent_question"]["options"]]:
        raise HTTPException(400, "Unknown value")
    service.answer_extent(doctor(), cid, body.value)
    return case_view(db.get_case(cid))


class Ask(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    language: str = "English"


@app.post("/api/cases/{cid}/messages", dependencies=[Depends(rate_limit("message"))])
def ask(cid: int, body: Ask, case: dict = Depends(owned_case)):
    check_language(body.language)
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


EXPERT_SPECIAL = ["other", "unusable"]


class ExpertAnswer(BaseModel):
    label: str
    note: str = Field(default="", max_length=2000)


@app.post("/api/expert/cases/{cid}", dependencies=[Depends(require_expert)])
def expert_answer(cid: int, body: ExpertAnswer):
    case = get_case_or_404(cid)
    # Only a disease of THIS crop: a wrong label would go into the live calibration and skew that crop's threshold.
    # "other" (a problem not in our list) and "unusable" (photo can't be judged) are stored, never calibrated on.
    valid = [d for d in doctor().classes if knowledge()["diseases"][d]["crop"] == case["crop"]] + EXPERT_SPECIAL
    if body.label not in valid:
        raise HTTPException(400, f"label must be one of {valid}")
    run = service.expert_answer(doctor(), cid, body.label, body.note.strip())
    return {"recalibrated": run is not None, "run": finite(run) if run else None}


@app.get("/api/expert/trust", dependencies=[Depends(require_expert)])
def trust():
    runs = db.calibration_runs()
    resets = [i for i, r in enumerate(runs) if (r["note"] or "").startswith("reset")]
    since = runs[resets[-1]:] if resets else runs
    return {"current": finite(runs[-1]) if runs else None, "since_reset": [finite(r) for r in since],
            "all": [finite(r) for r in runs[-200:]]}


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

