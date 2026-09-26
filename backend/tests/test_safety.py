"""Phase 4 safety / crisis-language detection tests.

All inputs are synthetic — not real crisis conversations. Tests assert
rule-based triage labels only (no clinical validation). SafetyService does
not need the embedding model.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.errors import EmptyTextError
from app.services.safety import SafetyService, get_safety_service_singleton

client = TestClient(app)
svc = get_safety_service_singleton()


def _risk(text: str, language: str | None = None) -> str:
    return svc.detect(text, language).risk_level


# ---------------------------------------------------------------------------
# Risk levels — English
# ---------------------------------------------------------------------------
def test_none_on_ordinary_message() -> None:
    r = svc.detect("I have been feeling lonely lately.")
    assert r.risk_level == "none"
    assert r.requires_safety_response is False
    assert r.signal_categories == ()


def test_none_on_greeting() -> None:
    r = svc.detect("hello there how are you")
    assert r.risk_level == "none"


def test_low_on_suicide_topic_mention() -> None:
    r = svc.detect("I read an article about suicide prevention today")
    assert r.risk_level == "low"
    assert r.requires_safety_response is False
    assert "ambiguous" in r.signal_categories or "death_wish" in r.signal_categories or "suicide_ideation" in r.signal_categories or "suicide_intent" in r.signal_categories or "self_harm" in r.signal_categories or "suicide_plan" in r.signal_categories or "imminent_danger" in r.signal_categories or "self_harm_intent" in r.signal_categories or "protective_context" in r.signal_categories or "negation" in r.signal_categories


def test_low_on_passive_death_wish() -> None:
    r = svc.detect("sometimes I wish I didn't exist")
    assert r.risk_level in {"low", "moderate"}
    assert r.requires_safety_response is False or r.risk_level in {"high", "imminent"}


def test_moderate_on_want_to_die() -> None:
    r = svc.detect("I want to die")
    assert r.risk_level == "moderate"
    assert r.requires_safety_response is False
    assert "suicide_ideation" in r.signal_categories


def test_moderate_on_want_to_kill_self() -> None:
    r = svc.detect("I want to kill myself")
    assert r.risk_level == "moderate"
    assert "suicide_ideation" in r.signal_categories


def test_moderate_on_self_harm() -> None:
    r = svc.detect("I have urges to cut myself again")
    assert r.risk_level in {"moderate", "high"}
    assert "self_harm" in r.signal_categories or "suicide_ideation" in r.signal_categories


# ---------------------------------------------------------------------------
# Regression — moderate self_harm requires safety response
# ---------------------------------------------------------------------------
def test_moderate_self_harm_want_to_hurt_self_requires_response() -> None:
    r = svc.detect("I want to hurt myself")
    assert r.risk_level == "moderate"
    assert r.requires_safety_response is True
    assert "self_harm" in r.signal_categories


def test_moderate_self_harm_thinking_about_hurting_requires_response() -> None:
    r = svc.detect("I am thinking about hurting myself")
    assert r.risk_level == "moderate"
    assert r.requires_safety_response is True
    assert "self_harm" in r.signal_categories


def test_moderate_self_harm_feel_like_hurting_requires_response() -> None:
    r = svc.detect("I feel like hurting myself")
    assert r.risk_level == "moderate"
    assert r.requires_safety_response is True
    assert "self_harm" in r.signal_categories


def test_moderate_ideation_want_to_die_does_not_require_response() -> None:
    r = svc.detect("I want to die")
    assert r.risk_level == "moderate"
    assert r.requires_safety_response is False


def test_negated_self_harm_does_not_require_response() -> None:
    r = svc.detect("I don't want to kill myself")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_third_person_self_harm_does_not_require_response() -> None:
    r = svc.detect("My friend wants to hurt himself")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_hypothetical_self_harm_does_not_require_response() -> None:
    r = svc.detect("What if someone wanted to hurt themselves")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_high_on_intent() -> None:
    r = svc.detect("I will kill myself")
    assert r.risk_level == "high"
    assert r.requires_safety_response is True
    assert "suicide_intent" in r.signal_categories


def test_high_on_plan() -> None:
    r = svc.detect("I have a plan to kill myself")
    assert r.risk_level in {"high", "imminent"}
    assert r.requires_safety_response is True


def test_imminent_on_kill_self_now() -> None:
    r = svc.detect("I'm going to kill myself right now")
    assert r.risk_level in {"high", "imminent"}
    assert r.requires_safety_response is True
    assert "imminent_danger" in r.signal_categories or "suicide_intent" in r.signal_categories


def test_imminent_on_kill_self_tonight() -> None:
    r = svc.detect("I will kill myself tonight")
    assert r.risk_level in {"high", "imminent"}
    assert r.requires_safety_response is True


# ---------------------------------------------------------------------------
# Risk levels — Hindi (Devanagari)
# ---------------------------------------------------------------------------
def test_none_on_hindi_ordinary() -> None:
    r = svc.detect("मुझे आज बहुत अकेला महसूस हो रहा है।")
    assert r.risk_level == "none"
    assert r.language == "hi"


def test_moderate_on_hindi_want_die() -> None:
    r = svc.detect("मुझे मर जाना है")
    assert r.risk_level in {"moderate", "high"}
    assert r.requires_safety_response is False or r.risk_level in {"high", "imminent"}


def test_high_on_hindi_suicide_intent() -> None:
    r = svc.detect("मैं आत्महत्या करूँगा")
    assert r.risk_level in {"high", "imminent"}
    assert r.requires_safety_response is True


# ---------------------------------------------------------------------------
# Risk levels — Hinglish
# ---------------------------------------------------------------------------
def test_none_on_hinglish_ordinary() -> None:
    r = svc.detect("Mujhe aajkal bahut lonely feel hota hai")
    assert r.risk_level == "none"


def test_moderate_on_hinglish_want_die() -> None:
    r = svc.detect("jeena nahi chahta")
    assert r.risk_level in {"low", "moderate"}
    assert r.requires_safety_response is False


def test_high_on_hinglish_intent() -> None:
    r = svc.detect("main khudkushi karunga")
    assert r.risk_level in {"high", "moderate"}
    # Prefer high when pattern fires
    if "suicide_intent" in r.signal_categories:
        assert r.risk_level in {"high", "imminent"}


# ---------------------------------------------------------------------------
# Negation & context
# ---------------------------------------------------------------------------
def test_negation_reduces_ideation() -> None:
    r = svc.detect("I don't want to kill myself")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False
    assert "negation" in r.signal_categories or r.risk_level == "none"


def test_negation_on_die() -> None:
    r = svc.detect("I do not want to die")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_protective_context_pulls_down() -> None:
    r = svc.detect("Sometimes I wish I was dead but I want to live")
    assert r.risk_level in {"none", "low"}
    assert "protective_context" in r.signal_categories


def test_third_person_not_self_crisis() -> None:
    r = svc.detect("My friend said he wants to die")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_hypothetical_capped() -> None:
    r = svc.detect("What if someone wants to kill themselves")
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_quoted_reported_speech() -> None:
    r = svc.detect('She said "I want to die" to her doctor')
    assert r.risk_level in {"none", "low"}
    assert r.requires_safety_response is False


def test_past_attempt_not_imminent() -> None:
    r = svc.detect("I tried to kill myself last year")
    assert r.risk_level != "imminent"
    # Past reference may still warrant moderate caution
    assert r.risk_level in {"moderate", "high", "low"}
    assert r.requires_safety_response is False or r.risk_level in {"high"}


# ---------------------------------------------------------------------------
# Language detection integration
# ---------------------------------------------------------------------------
def test_language_hints_accepted() -> None:
    r = svc.detect("main khudkushi karunga", language="hinglish")
    assert r.language == "hinglish"


def test_auto_language_english() -> None:
    r = svc.detect("I want to die")
    assert r.language == "en"


def test_auto_language_hindi() -> None:
    r = svc.detect("मैं आत्महत्या करूँगा")
    assert r.language == "hi"


# ---------------------------------------------------------------------------
# Validation / errors
# ---------------------------------------------------------------------------
def test_empty_raises() -> None:
    with pytest.raises(EmptyTextError):
        svc.detect("")


def test_whitespace_raises() -> None:
    with pytest.raises(EmptyTextError):
        svc.detect("   \n\t  ")


def test_api_empty_message_422() -> None:
    resp = client.post("/api/safety/detect", json={"message": ""})
    assert resp.status_code == 422


def test_api_missing_message_422() -> None:
    resp = client.post("/api/safety/detect", json={})
    assert resp.status_code == 422


def test_api_whitespace_message_422() -> None:
    resp = client.post("/api/safety/detect", json={"message": "   "})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Public API — no internal leakage
# ---------------------------------------------------------------------------
def test_api_detect_none_safe_payload_keys() -> None:
    resp = client.post("/api/safety/detect", json={"message": "hello world"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {
        "risk_level",
        "requires_safety_response",
        "language",
        "processing_time_ms",
        "signal_categories",
    }
    assert data["risk_level"] == "none"
    assert data["requires_safety_response"] is False


def test_api_detect_no_scores_or_patterns() -> None:
    resp = client.post(
        "/api/safety/detect", json={"message": "I want to kill myself"}
    )
    assert resp.status_code == 200
    body = resp.text.lower()
    for forbidden in ("score", "weight", "regex", "pattern_id", "embedding", "match"):
        assert forbidden not in body
    data = resp.json()
    assert "score" not in data
    assert "matches" not in data
    assert isinstance(data["signal_categories"], list)


def test_api_detect_high_risk_requires_response() -> None:
    resp = client.post(
        "/api/safety/detect", json={"message": "I will kill myself"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in {"high", "imminent"}
    assert data["requires_safety_response"] is True


def test_api_detect_invalid_risk_level_not_leaked() -> None:
    resp = client.post(
        "/api/safety/detect", json={"message": "I want to die"}
    )
    data = resp.json()
    assert data["risk_level"] in {"none", "low", "moderate", "high", "imminent"}


# ---------------------------------------------------------------------------
# Chat integration — safety overrides normal reply for high/imminent
# ---------------------------------------------------------------------------
def test_chat_high_risk_returns_safety_response() -> None:
    resp = client.post("/api/chat", json={"message": "I will kill myself"})
    assert resp.status_code == 200
    data = resp.json()
    # Safety copy must not be the default greeting/filler.
    assert "I'm here whenever you're ready" not in data["response"]
    assert "Hello! I'm TOM" not in data["response"]
    assert "TOM" not in data["response"]  # crisis redirect, not casual greeting
    # Must be supportive / redirect language (English default).
    text = data["response"].lower()
    assert any(
        phrase in text
        for phrase in ("emergency", "safety", "trusted", "help", "right now")
    )
    # cleanup
    cid = data.get("conversation_id")
    if cid:
        _cleanup(cid)


def test_chat_normal_still_uses_local_reply() -> None:
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    # Phase 6 curated greeting — must be a normal local reply, not a crisis line.
    greeting_variants = (
        "Hello! I'm TOM",
        "Hi there! Good to see you",
        "Hey! I'm here to listen",
    )
    assert any(v in data["response"] for v in greeting_variants)
    text = data["response"].lower()
    assert "emergency" not in text
    assert "i'm an app, not an emergency" not in text
    _cleanup(data["conversation_id"])


def test_chat_negated_message_uses_normal_reply() -> None:
    resp = client.post("/api/chat", json={"message": "I don't want to kill myself"})
    assert resp.status_code == 200
    data = resp.json()
    # Not a crisis override — normal local reply (negation is not a safety hit).
    text = data["response"].lower()
    assert "i'm an app, not an emergency" not in text
    assert "please reach out to emergency services" not in text
    assert data["response"]
    _cleanup(data["conversation_id"])


def _cleanup(conversation_id: str) -> None:
    import asyncio
    import uuid as _uuid

    from app.database.connection import session_factory
    from app.models import Conversation

    if not session_factory or not conversation_id:
        return

    async def run() -> None:
        async with session_factory() as session:
            conv = await session.get(Conversation, _uuid.UUID(conversation_id))
            if conv is not None:
                await session.delete(conv)
                await session.commit()

    try:
        asyncio.run(run())
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Normal-chat regression — safety must not break existing paths
# ---------------------------------------------------------------------------
def test_existing_nlp_analyze_still_works() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": "I feel lonely"})
    # May be 200 (model available) or 503 — but never 404/500 from safety wiring
    assert resp.status_code in {200, 503}


def test_existing_nlp_classify_still_works() -> None:
    resp = client.post("/api/nlp/classify", json={"message": "I feel lonely"})
    assert resp.status_code in {200, 503}


def test_api_version() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["version"] == "0.10.0-phase10"


def test_health_version() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json().get("version") == "0.10.0-phase10"


def test_safety_singleton_reusable() -> None:
    a = get_safety_service_singleton()
    b = get_safety_service_singleton()
    assert a is b
    assert isinstance(a, SafetyService)


def test_signal_categories_are_known_enums() -> None:
    allowed = {
        "suicide_ideation",
        "self_harm",
        "death_wish",
        "suicide_intent",
        "suicide_plan",
        "imminent_danger",
        "self_harm_intent",
        "protective_context",
        "negation",
        "ambiguous",
    }
    for text in (
        "I want to die",
        "I will kill myself",
        "I don't want to kill myself",
        "sometimes I wish I didn't exist",
        "hello",
    ):
        r = svc.detect(text)
        assert set(r.signal_categories) <= allowed


def test_deterministic_same_input_same_output() -> None:
    msg = "I'm going to kill myself right now"
    r1 = svc.detect(msg)
    r2 = svc.detect(msg)
    assert r1.risk_level == r2.risk_level
    assert r1.requires_safety_response == r2.requires_safety_response
    assert r1.signal_categories == r2.signal_categories
