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
    diseases = set(knowledge()["diseases"])
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
