"""Tests for the treatment notes, retrieval and the LLM guardrails (no API key or network needed)."""
from __future__ import annotations

import pytest

from crop_doctor.assistant import llm
from crop_doctor.assistant.decision import knowledge
from crop_doctor.knowledge.rag import Retriever, load_chunks

STANDARD = {"Symptoms", "Why it spreads", "What to do now", "Organic and low-cost options", "Chemical options",
            "Prevention next season"}


@pytest.fixture(scope="module")
def retriever():
    return Retriever(use_embeddings=False)  # TF-IDF: fast and offline for tests


def test_every_disease_has_a_sourced_note():
    chunks = load_chunks()
    diseases = set(knowledge()["diseases"]) - {"tomato_something_else"}   # Exp 10: never gets treatment advice
    by_disease = {}
    for c in chunks:
        by_disease.setdefault(c.disease, set()).add(c.section)
        assert c.sources, f"{c.id} has no sources"
        assert all(s.split(": ")[-1].startswith("http") for s in c.sources), c.sources
    assert diseases <= set(by_disease)
    for d in {x for x in diseases if not x.endswith("_healthy")}:
        assert STANDARD <= by_disease[d], (d, STANDARD - by_disease[d])


def test_search_stays_within_the_diagnosed_disease(retriever):
    for c in retriever.search("which chemical spray should I use", "tomato_septoria", k=5):
        assert c.disease in ("tomato_septoria", "general")
    assert sum(c.disease == "general" for c in retriever.search("spray safety label", "tomato_septoria", k=5)) <= 1


def test_first_reply_context_has_actions_and_safety(retriever):
    ids = [c.id for c in retriever.first_reply_context("tomato_late_blight")]
    assert ids[0] == "tomato_late_blight#What to do now"
    assert "general#Before spraying" in ids


def test_guardrail_catches_other_diseases():
    allowed = ["tomato_early_blight"]
    assert llm.mentions_forbidden_disease("Most likely early blight. Remove lower leaves.", allowed) is None
    assert "late blight" in llm.mentions_forbidden_disease("This could also be late blight.", allowed)
    assert llm.mentions_forbidden_disease("Looks like Septoria leaf spot", allowed) == "Tomato Septoria leaf spot"
    # Potato early blight shares the name "early blight": not a violation when tomato early blight is allowed.
    assert llm.mentions_forbidden_disease("early blight on potato and tomato", allowed) is None


def test_reply_without_api_key_uses_template(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assessment = {"status": "diagnosis", "crop": "tomato", "label": "tomato_septoria", "probability": 0.9,
                  "shortlist": ["tomato_septoria"], "message": "Most likely: Tomato Septoria leaf spot."}
    r = llm.reply(assessment)
    assert not r.used_llm and "no API key" in r.fallback_reason
    assert "Septoria" in r.text and r.sources
    assert "tomato_septoria#What to do now" in r.note_ids


def test_retake_reply_has_no_treatment(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = llm.reply({"status": "retake", "message": "The photo is blurry."})
    assert r.text == "The photo is blurry." and r.note_ids == []


SEPTORIA = {"status": "diagnosis", "crop": "tomato", "label": "tomato_septoria", "probability": 0.9,
            "shortlist": ["tomato_septoria"], "message": "Most likely: Tomato Septoria leaf spot."}


def test_provider_choice(monkeypatch):
    assert llm.provider() is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert llm.provider() == "claude"
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    assert llm.provider() == "gemini"                      # Gemini wins when both are set...
    monkeypatch.setenv("CROP_DOCTOR_LLM", "claude")
    assert llm.provider() == "claude"                      # ...unless Claude is chosen explicitly


def test_gemini_reply_passes_guardrail(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    seen = {}

    def fake(system, history, user_text):
        seen.update(system=system, user=user_text)
        return "Most likely Septoria leaf spot. Remove lower leaves. Confirm with a local expert before spraying."
    monkeypatch.setattr(llm, "_ask_gemini", fake)
    r = llm.reply(SEPTORIA, language="Hindi")
    assert r.used_llm and "Septoria" in r.text and r.sources
    assert "Reply in Hindi" in seen["system"] and "<allowed_diseases>" in seen["user"]


def test_gemini_reply_naming_other_disease_is_replaced(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.setattr(llm, "_ask_gemini", lambda *a: "This could also be late blight.")
    r = llm.reply(SEPTORIA)
    assert not r.used_llm and "guardrail" in r.fallback_reason


def test_gemini_failure_falls_back_to_template(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "y")

    def boom(*a):
        raise llm.Declined("status failed")
    monkeypatch.setattr(llm, "_ask_gemini", boom)
    r = llm.reply(SEPTORIA)
    assert not r.used_llm and r.fallback_reason == "gemini: status failed" and "Septoria" in r.text
    monkeypatch.setattr(llm, "_ask_gemini", lambda *a: (_ for _ in ()).throw(ConnectionError()))
    assert llm.reply(SEPTORIA).fallback_reason == "gemini unavailable: ConnectionError"


def test_gemini_with_bad_key_still_answers(monkeypatch):
    """Real SDK, fake key: the request fails (no network or 400) and the farmer still gets the template."""
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    r = llm.reply(SEPTORIA)
    assert not r.used_llm and r.fallback_reason.startswith("gemini") and "Septoria" in r.text
