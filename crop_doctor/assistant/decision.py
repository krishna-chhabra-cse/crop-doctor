"""What should the assistant DO with the model's output? Pure logic, no model, so it's easy to test.

Inputs: crop-aware, temperature-scaled probabilities, plus the conformal shortlist (randomised APS).

    shortlist empty            -> EXPERT    ("this photo doesn't look like anything I know well")
    shortlist = 1 disease      -> DIAGNOSIS ("most likely X"; never presented as certain: 1-disease
                                             shortlists were right 77% of the time on field_test)
    shortlist = healthy only   -> HEALTHY
    shortlist 2-3 diseases     -> QUESTION  (a visual question that separates them), then
                                  answer updates the probabilities (Bayes rule) -> DIAGNOSIS or EXPERT
    shortlist > 3              -> EXPERT

Urgency comes from how fast the disease spreads, how much of the crop the farmer says is affected,
and (only as a tie-breaker) the colour-based severity estimate of the photo.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from crop_doctor.uncertainty.conformal import prediction_sets

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge" / "diseases.json"
MAX_QUESTION_SET = 3
ANSWER_TRUST = 0.8          # we assume the farmer's answer to a visual question is right 80% of the time
AFTER_ANSWER_THRESHOLD = 0.75
def is_healthy(label: str) -> bool:
    return label.endswith("_healthy")


@lru_cache(maxsize=1)
def knowledge() -> dict:
    return json.loads(KNOWLEDGE.read_text(encoding="utf-8"))


def disease_name(label: str) -> str:
    return knowledge()["diseases"][label]["name"]


# ---------- follow-up questions ----------

def choose_question(shortlist: list[str], asked: set[str] = frozenset()) -> dict | None:
    """Pick the question whose options split the shortlist best (most options that point to a shortlisted disease)."""
    best, best_score = None, 1
    for q in knowledge()["follow_up_questions"]:
        if q["id"] in asked:
            continue
        hit_options = [o for o in q["options"] if set(o["favours"]) & set(shortlist)]
        covered = set().union(*(set(o["favours"]) & set(shortlist) for o in hit_options)) if hit_options else set()
        score = len(hit_options) if len(covered) >= 2 else 0   # useless unless it separates >= 2 candidates
        if score > best_score:
            best, best_score = q, score
    return best


def apply_answer(probs: np.ndarray, classes: list[str], favours: list[str], trust: float = ANSWER_TRUST) -> np.ndarray:
    """Bayes rule: P(disease | answer) is proportional to P(answer | disease) * P(disease).
    P(answer | disease) = trust if the answer points to that disease, else 1 - trust."""
    like = np.array([trust if c in favours else 1 - trust for c in classes])
    post = probs * like
    return post / post.sum()


# ---------- urgency ----------

def urgency(label: str, extent: str | None = None, severity_band: str | None = None) -> dict:
    """extent: farmer's answer 'few' | 'some' | 'many' (or None). severity_band: from the photo, a tie-breaker."""
    spread = knowledge()["diseases"][label]["spread"]
    if spread == "none":
        return {"level": "none", "act_within": None, "why": "No disease detected."}
    if spread == "fast":
        return {"level": "urgent", "act_within": "24 hours",
                "why": "This disease can spread through a whole field within days."}
    if spread == "virus_insect":
        level = "urgent" if extent == "many" else "soon"
        return {"level": level, "act_within": "24 hours" if level == "urgent" else "2-3 days",
                "why": "There is no cure for a virus. Remove infected plants and control the insects (whiteflies) that spread it."}
    if spread == "virus_contact":
        return {"level": "soon", "act_within": "2-3 days",
                "why": "There is no cure for a virus. Remove infected plants; it spreads on hands and tools."}
    # spread == "medium" (most fungal / bacterial leaf spots)
    if extent == "many" or (extent is None and severity_band == "severe"):
        return {"level": "urgent", "act_within": "2 days", "why": "Already widespread; it will keep spreading."}
    if extent == "some" or (extent is None and severity_band in ("moderate", "unknown", None)):
        return {"level": "soon", "act_within": "3 days", "why": "Treat before it spreads to more plants."}
    return {"level": "routine", "act_within": "this week", "why": "Caught early. Remove affected leaves and keep watching."}


# ---------- the decision ----------

def decide(probs: np.ndarray, classes: list[str], qhat: float, u: float,
           answer: dict | None = None, asked: set[str] = frozenset()) -> dict:
    """probs: (n_classes,) crop-aware probabilities for ONE photo. u: its randomised-APS noise value.
    answer: {"question_id": ..., "favours": [...]} if the farmer answered a follow-up question."""
    sets = prediction_sets(probs[None, :], qhat, np.array([u]))[0]
    order = np.argsort(-probs)
    shortlist = [classes[i] for i in order if sets[i]]
    top = [{"label": classes[i], "name": disease_name(classes[i]), "probability": round(float(probs[i]), 3)}
           for i in order[:3] if probs[i] > 0]
    out = {"shortlist": shortlist, "top": top}

    if answer is not None:
        post = apply_answer(probs, classes, answer["favours"])
        j = int(post.argmax())
        out["after_answer"] = [{"label": classes[i], "probability": round(float(post[i]), 3)}
                               for i in np.argsort(-post)[:3] if post[i] > 0]
        if post[j] >= AFTER_ANSWER_THRESHOLD and classes[j] in shortlist:
            status = "healthy" if is_healthy(classes[j]) else "diagnosis"
            return {**out, "status": status, "label": classes[j], "probability": round(float(post[j]), 3),
                    "via": "follow_up_question"}
        return {**out, "status": "expert", "reason": "still unsure after your answer"}

    if len(shortlist) == 0:
        return {**out, "status": "expert", "reason": "the photo doesn't look like the diseases I know well"}
    if len(shortlist) == 1:
        label = shortlist[0]
        return {**out, "status": "healthy" if is_healthy(label) else "diagnosis", "label": label,
                "probability": round(float(probs[classes.index(label)]), 3), "via": "model"}
    if len(shortlist) <= MAX_QUESTION_SET:
        q = choose_question(shortlist, asked)
        if q is not None:
            return {**out, "status": "question", "question": q}
    return {**out, "status": "expert", "reason": f"{len(shortlist)} diseases are still possible"}
