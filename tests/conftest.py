"""Shared test setup: never call a real AI service from tests, whatever keys are set on this machine."""
import pytest

LLM_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GEMINI_API_KEY", "GOOGLE_API_KEY", "CROP_DOCTOR_LLM")


@pytest.fixture(autouse=True)
def no_llm_keys(monkeypatch):
    for k in LLM_KEYS:
        monkeypatch.delenv(k, raising=False)
