"""The chat reply: turn the pipeline's decision + retrieved treatment notes into a friendly answer.

Golden rule: the vision pipeline decides the disease; the LLM only EXPLAINS it.
Guardrails:
  1. The prompt gives the LLM the decision and the retrieved notes only, and tells it to use nothing else.
  2. After it answers, we check it didn't name a disease outside the allowed list; if it did, we
     discard its answer and use the template reply instead.
  3. Any API problem (no key, network, refusal) -> template reply. The app always works.

Two interchangeable providers (same prompt, same guardrails), picked by which key is set:
- Gemini: GEMINI_API_KEY (or GOOGLE_API_KEY). Model GEMINI_MODEL, default gemini-3.6-flash (stable, fast).
- Claude: ANTHROPIC_API_KEY. Model CROP_DOCTOR_MODEL, default Claude Opus 5.5 at low effort.
If both keys are set, Gemini is used unless CROP_DOCTOR_LLM=claude. No key -> template replies.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from crop_doctor.assistant.decision import disease_name, knowledge
from crop_doctor.knowledge.rag import Chunk, default_retriever

MODEL = os.environ.get("CROP_DOCTOR_MODEL", "claude-opus-5-5")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class Declined(Exception):
    """The model refused or returned no usable text -> template reply."""

SYSTEM_PROMPT = """You are Crop Doctor, a friendly assistant for smallholder farmers growing tomato and potato.

How you work:
- A separate vision system has already examined the farmer's leaf photo. Its result is in <assessment>.
  You never change, add or second-guess a diagnosis. You explain what the assessment says.
- Use only facts from <assessment> and <notes>. Each note has an id; mention the sources you used at the end
  as "Sources:" followed by the note titles. If the notes don't answer the farmer's question, say so and suggest
  asking the local agriculture officer or KVK.
- Name only the diseases listed in <allowed_diseases>. Never suggest any other disease.
- A "diagnosis" is a most-likely result, not a certainty: say "most likely". Always end treatment advice with a
  reminder to confirm with a local expert before spraying.
- If status is "expert", explain kindly that the photo has been sent to an expert and what the farmer can safely
  do meanwhile (from the notes). If status is "question", ask the question exactly as given, listing the options.
- Mention the urgency (act within ...) early when it is "urgent".
- Write for a farmer: short sentences, no jargon, at most about 150 words, simple bullet points for steps.
- Reply in {language}."""


def _gemini_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _claude_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def provider() -> str | None:
    """'gemini', 'claude' or None (template replies)."""
    forced = os.environ.get("CROP_DOCTOR_LLM", "").lower()
    if forced in ("gemini", "claude"):
        return forced if (_gemini_key() if forced == "gemini" else _claude_key()) else None
    return "gemini" if _gemini_key() else "claude" if _claude_key() else None


def llm_available() -> bool:
    return provider() is not None


@dataclass
class Reply:
    text: str
    sources: list[str] = field(default_factory=list)
    used_llm: bool = False
    note_ids: list[str] = field(default_factory=list)
    fallback_reason: str | None = None


def allowed_diseases(assessment: dict) -> list[str]:
    labels = set(assessment.get("shortlist", []))
    if assessment.get("label"):
        labels.add(assessment["label"])
    return sorted(labels)


def gather_notes(assessment: dict, question: str | None) -> list[Chunk]:
    r = default_retriever()
    label = assessment.get("label")
    if label and question:
        return r.search(question, disease=label, k=4)
    if label:
        return r.first_reply_context(label)
    # No single disease: give "what to do now" for the top candidates + general safety.
    notes = [c for lab in assessment.get("shortlist", [])[:2] for c in r.search("what to do now", disease=lab, k=1)]
    return notes + r.search("before spraying safety", disease="general", k=1)


def _assessment_block(a: dict) -> str:
    lines = [f"status: {a['status']}", f"crop: {a.get('crop')}"]
    if a.get("label"):
        lines.append(f"most likely disease: {disease_name(a['label'])} (probability {a.get('probability', 0):.0%})")
    if a.get("shortlist"):
        lines.append("possible diseases (shortlist): " + ", ".join(disease_name(c) for c in a["shortlist"]))
    if a.get("urgency"):
        u = a["urgency"]
        lines.append(f"urgency: {u['level']}; act within {u['act_within']}; reason: {u['why']}")
    sev = a.get("severity_estimate")
    if sev and sev.get("fraction") is not None:
        lines.append(f"damaged leaf area (rough colour-based estimate): {sev['fraction']:.0%}")
    if a.get("status") == "question":
        q = a["question"]
        lines.append("question to ask: " + q["question"] + " Options: " + " | ".join(o["text"] for o in q["options"]))
    if a.get("reason"):
        lines.append(f"reason: {a['reason']}")
    if a.get("status") == "retake":
        lines.append(f"retake advice: {a.get('message')}")
    return "\n".join(lines)


def template_reply(assessment: dict, notes: list[Chunk], reason: str | None = None) -> Reply:
    """No-LLM answer: the pipeline's message + the first relevant note, with sources. Always available."""
    text = assessment.get("message", "")
    action = next((c for c in notes if c.section in ("What to do now", "Organic and low-cost options")), None)
    if action and assessment.get("status") in ("diagnosis", "healthy", "expert"):
        text += f"\n\nWhat you can do ({action.title}): {action.text}"
    sources = sorted({s for c in notes for s in c.sources})
    return Reply(text, sources, used_llm=False, note_ids=[c.id for c in notes], fallback_reason=reason)


def mentions_forbidden_disease(text: str, allowed: list[str]) -> str | None:
    """Return the name of a disease the reply mentions but isn't allowed to (guardrail 2)."""
    low = text.lower()
    for label, d in knowledge()["diseases"].items():
        if label in allowed or label.endswith("healthy"):
            continue
        names = {d["name"].lower(), d["name"].lower().replace("tomato ", "").replace("potato ", "")}
        # Same disease name on the other crop (e.g. "early blight" for potato vs tomato) is fine.
        allowed_names = {knowledge()["diseases"][a]["name"].lower().split(" ", 1)[-1] for a in allowed}
        for n in names:
            if n and n not in allowed_names and n in low:
                return d["name"]
    return None


def reply(assessment: dict, question: str | None = None, history: list[dict] | None = None,
          language: str = "English") -> Reply:
    """assessment: dict from CropDoctor.assess(). question: the farmer's follow-up text (None = first reply)."""
    notes = [] if assessment.get("status") == "retake" else gather_notes(assessment, question)
    allowed = allowed_diseases(assessment)
    which = provider()
    if which is None:
        return template_reply(assessment, notes, "no API key set (GEMINI_API_KEY or ANTHROPIC_API_KEY)")
    notes_xml = "\n".join(f'<note id="{c.id}" title="{c.title} - {c.section}">{c.text}</note>' for c in notes)
    context = (f"<assessment>\n{_assessment_block(assessment)}\n</assessment>\n"
               f"<allowed_diseases>{', '.join(disease_name(a) for a in allowed) or 'none'}</allowed_diseases>\n"
               f"<notes>\n{notes_xml}\n</notes>")
    user_text = f"{context}\n\nFarmer: {question or 'Please explain the result of my photo and what I should do.'}"
    system = SYSTEM_PROMPT.format(language=language)
    try:
        call = _ask_gemini if which == "gemini" else _ask_claude
        text = call(system, list(history or []), user_text).strip()
        if not text:
            raise Declined("empty reply")
    except Declined as e:
        return template_reply(assessment, notes, f"{which}: {e}")
    except Exception as e:  # noqa: BLE001 - offline, bad key, rate limit...: the app must still answer
        return template_reply(assessment, notes, f"{which} unavailable: {type(e).__name__}")
    bad = mentions_forbidden_disease(text, allowed)
    if bad:
        return template_reply(assessment, notes, f"guardrail: reply mentioned {bad}")
    return Reply(text, sorted({s for c in notes for s in c.sources}), used_llm=True, note_ids=[c.id for c in notes])


def _ask_claude(system: str, history: list[dict], user_text: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.with_options(timeout=60.0, max_retries=1).beta.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system,
        messages=history + [{"role": "user", "content": user_text}],
        output_config={"effort": "low"},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise Declined("model declined")
    return "".join(b.text for b in resp.content if b.type == "text")


def _ask_gemini(system: str, history: list[dict], user_text: str) -> str:
    """Gemini Interactions API, stateless (store=False): earlier chat turns are included as text."""
    from google import genai
    client = genai.Client(api_key=_gemini_key())
    earlier = "\n".join(f"{'Farmer' if m['role'] == 'user' else 'Crop Doctor'}: {m['content']}" for m in history)
    prompt = (f"<earlier_conversation>\n{earlier}\n</earlier_conversation>\n\n{user_text}" if earlier else user_text)
    it = client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=system,
        input=prompt,
        generation_config={"max_output_tokens": 1500},
        store=False,                       # don't keep farmers' conversations on Google's servers
        timeout=60.0,
    )
    if it.status != "completed":
        raise Declined(f"status {it.status}")
    return it.output_text or ""
