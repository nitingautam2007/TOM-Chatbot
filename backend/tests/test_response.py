"""Phase 6 — local response generation tests.

Covers curated selection, multilingual output, safety priority, context,
fallbacks, NLP failure handling, persistence, and validation.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.connection import session_factory
from app.main import app
from app.models import Conversation, Message
from app.services.errors import EmptyTextError, NLPUnavailableError
from app.services.nlp.types import ClassificationResult, EmotionResult, IntentResult
from app.services.response import (
    EMOTION_RESPONSES,
    FALLBACK_RESPONSES,
    INTENT_RESPONSES,
    GeneratedResponse,
    ResponseContext,
    ResponseSelector,
)
from app.services.response.library import LANGS
from app.services.safety.service import SafetyService

client = TestClient(app)
selector = ResponseSelector()
safety = SafetyService()


def _cleanup_conversation(conversation_id: str) -> None:
    if session_factory is None or not conversation_id:
        return

    async def run() -> None:
        async with session_factory() as session:
            conversation = await session.get(Conversation, uuid.UUID(conversation_id))
            if conversation is not None:
                await session.delete(conversation)
                await session.commit()

    asyncio.run(run())


def _ctx(
    message: str,
    *,
    language: str = "en",
    intent: str | None = None,
    intent_confidence: float = 1.0,
    emotion: str | None = None,
    emotion_confidence: float = 1.0,
    recent: tuple[str, ...] = (),
) -> ResponseContext:
    return ResponseContext(
        message=message,
        language=language,  # type: ignore[arg-type]
        intent=intent,
        intent_confidence=intent_confidence,
        emotion=emotion,
        emotion_confidence=emotion_confidence,
        recent_messages=recent,
    )


# ---------------------------------------------------------------------------
# Library completeness
# ---------------------------------------------------------------------------
REQUIRED_INTENTS = {
    "greeting",
    "goodbye",
    "general_conversation",
    "emotional_support",
    "stress",
    "anxiety",
    "sadness",
    "loneliness",
    "academic_pressure",
    "relationship_issue",
    "sleep_concern",
    "self_confidence",
    "coping_help",
    "help_seeking",
    "unknown",
}

REQUIRED_EMOTIONS = {
    "sadness",
    "anxiety",
    "anger",
    "stress",
    "loneliness",
    "happiness",
    "positive",
    "neutral",
    "mixed",
    "uncertain",
}


def test_library_covers_all_intents_and_languages() -> None:
    assert set(INTENT_RESPONSES) == REQUIRED_INTENTS
    for intent, by_lang in INTENT_RESPONSES.items():
        for lang in LANGS:
            assert lang in by_lang, f"{intent} missing {lang}"
            assert by_lang[lang], f"{intent}/{lang} empty"


def test_library_covers_all_emotions_and_languages() -> None:
    assert set(EMOTION_RESPONSES) == REQUIRED_EMOTIONS
    for emotion, by_lang in EMOTION_RESPONSES.items():
        for lang in LANGS:
            assert lang in by_lang and by_lang[lang]


def test_fallback_library_complete() -> None:
    for lang in LANGS:
        assert FALLBACK_RESPONSES.get(lang)


# ---------------------------------------------------------------------------
# Intent / emotion / language selection (unit)
# ---------------------------------------------------------------------------
def test_english_greeting_response() -> None:
    out = selector.generate(_ctx("hello", intent="greeting"))
    assert out.language == "en"
    assert out.source in {"intent", "context"}
    assert out.text in INTENT_RESPONSES["greeting"]["en"]
    assert not out.is_safety


def test_hindi_language_response() -> None:
    out = selector.generate(
        _ctx("नमस्ते", language="hi", intent="greeting", emotion="neutral")
    )
    assert out.language == "hi"
    assert out.text in INTENT_RESPONSES["greeting"]["hi"]
    assert any("ऀ" <= ch <= "ॿ" for ch in out.text)


def test_hinglish_language_response() -> None:
    out = selector.generate(
        _ctx(
            "mujhe bahut akela lag raha hai",
            language="hinglish",
            intent="loneliness",
            emotion="loneliness",
        )
    )
    assert out.language == "hinglish"
    assert out.text in INTENT_RESPONSES["loneliness"]["hinglish"]


def test_goodbye_intent() -> None:
    out = selector.generate(_ctx("bye", intent="goodbye"))
    assert out.text in INTENT_RESPONSES["goodbye"]["en"]


def test_general_conversation_intent() -> None:
    out = selector.generate(_ctx("just hanging out", intent="general_conversation"))
    assert out.text in INTENT_RESPONSES["general_conversation"]["en"]


def test_stress_intent() -> None:
    out = selector.generate(_ctx("I am very stressed", intent="stress"))
    assert out.text in INTENT_RESPONSES["stress"]["en"]


def test_anxiety_intent() -> None:
    out = selector.generate(_ctx("I worry a lot", intent="anxiety"))
    assert out.text in INTENT_RESPONSES["anxiety"]["en"]


def test_sadness_intent() -> None:
    out = selector.generate(_ctx("I feel sad", intent="sadness"))
    assert out.text in INTENT_RESPONSES["sadness"]["en"]


def test_loneliness_intent() -> None:
    out = selector.generate(_ctx("I feel lonely", intent="loneliness"))
    assert out.text in INTENT_RESPONSES["loneliness"]["en"]


def test_academic_pressure_intent() -> None:
    out = selector.generate(_ctx("exams overwhelm me", intent="academic_pressure"))
    assert out.text in INTENT_RESPONSES["academic_pressure"]["en"]


def test_relationship_issue_intent() -> None:
    out = selector.generate(_ctx("we keep fighting", intent="relationship_issue"))
    assert out.text in INTENT_RESPONSES["relationship_issue"]["en"]


def test_sleep_concern_intent() -> None:
    out = selector.generate(_ctx("I cannot sleep", intent="sleep_concern"))
    assert out.text in INTENT_RESPONSES["sleep_concern"]["en"]


def test_self_confidence_intent() -> None:
    out = selector.generate(_ctx("I doubt myself", intent="self_confidence"))
    assert out.text in INTENT_RESPONSES["self_confidence"]["en"]


def test_coping_help_intent() -> None:
    out = selector.generate(_ctx("how do I cope", intent="coping_help"))
    assert out.text in INTENT_RESPONSES["coping_help"]["en"]


def test_help_seeking_intent() -> None:
    out = selector.generate(_ctx("I need help finding support", intent="help_seeking"))
    assert out.text in INTENT_RESPONSES["help_seeking"]["en"]


def test_unknown_intent_uses_semantic_or_fallback() -> None:
    out = selector.generate(
        _ctx("xqz plugh frobnicate", intent="unknown", intent_confidence=0.1)
    )
    assert out.source in {"semantic", "fallback", "emotion"}
    assert out.text


def test_uncertain_emotion_falls_through() -> None:
    out = selector.generate(
        _ctx(
            "hm not sure",
            intent="unknown",
            intent_confidence=0.0,
            emotion="uncertain",
            emotion_confidence=0.9,
        )
    )
    assert out.source in {"semantic", "fallback"}
    assert out.text in {
        *FALLBACK_RESPONSES["en"],
        *sum(
            (list(v["en"]) for v in INTENT_RESPONSES.values()),
            [],
        ),
    }


def test_low_confidence_intent_skips_intent_run() -> None:
    out = selector.generate(
        _ctx("hm", intent="stress", intent_confidence=0.1, emotion="neutral", emotion_confidence=0.1)
    )
    assert out.source != "intent"
    assert out.text


def test_emotion_used_when_intent_unknown() -> None:
    out = selector.generate(
        _ctx(
            "not sure what to say",
            intent="unknown",
            intent_confidence=0.0,
            emotion="sadness",
            emotion_confidence=0.8,
        )
    )
    assert out.source == "emotion"
    assert out.text in EMOTION_RESPONSES["sadness"]["en"]


def test_unknown_language_defaults_to_english() -> None:
    out = selector.generate(
        _ctx("???", language="unknown", intent="greeting")
    )
    assert out.language == "en"


# ---------------------------------------------------------------------------
# Context + variation
# ---------------------------------------------------------------------------
def test_context_rotation_changes_variant() -> None:
    first = selector.generate(_ctx("I am stressed", intent="stress"))
    recent = ("I am stressed", first.text, "still stressed about work")
    second = selector.generate(_ctx("I am stressed", intent="stress", recent=recent))
    variants = INTENT_RESPONSES["stress"]["en"]
    if len(variants) > 1:
        # Deterministic: window length selects a different start index.
        assert second.text in variants
        assert first.text in variants


def test_context_repeat_same_text_avoided_when_possible() -> None:
    variants = INTENT_RESPONSES["greeting"]["en"]
    first = variants[0]
    out = selector.generate(_ctx("hello", intent="greeting", recent=(first,)))
    assert out.text in variants
    if len(variants) > 1:
        assert out.text != first


def test_repeated_equivalent_messages_stable() -> None:
    a = selector.generate(_ctx("I feel stressed about college", intent="stress"))
    b = selector.generate(_ctx("I feel stressed about college", intent="stress"))
    assert a.text == b.text
    assert a.source == b.source


# ---------------------------------------------------------------------------
# Semantic + fallback
# ---------------------------------------------------------------------------
def test_semantic_or_fallback_for_low_confidence() -> None:
    out = selector.generate(
        _ctx(
            "exams pressure is too much for me right now",
            intent="unknown",
            intent_confidence=0.0,
            emotion="uncertain",
            emotion_confidence=0.0,
        )
    )
    assert out.source in {"semantic", "fallback"}
    assert out.text


def test_semantic_threshold_disabled_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(settings, "response_semantic_threshold", 0.0)
    out = selector.generate(
        _ctx("anything at all", intent="unknown", intent_confidence=0.0)
    )
    assert out.source == "fallback"
    assert out.text in FALLBACK_RESPONSES["en"]


def test_selector_failure_safe_empty_message() -> None:
    out = selector.generate(_ctx("   ", language="unknown"))
    assert out.text
    assert out.source in {"semantic", "fallback"}


# ---------------------------------------------------------------------------
# Safety priority (unit + API)
# ---------------------------------------------------------------------------
def test_safety_high_bypasses_normal_generation() -> None:
    result = safety.detect("I will kill myself")
    assert result.requires_safety_response is True
    reply = safety.response_for(result)
    # Crisis copy — never a normal curated intent line.
    for variants in INTENT_RESPONSES.values():
        assert reply not in variants.get("en", ())


def test_safety_imminent_bypasses_normal_generation() -> None:
    result = safety.detect("I am about to kill myself")
    assert result.risk_level in {"high", "imminent"}
    assert result.requires_safety_response is True
    reply = safety.response_for(result)
    assert reply
    for variants in INTENT_RESPONSES.values():
        assert reply not in variants.get("en", ())


def test_normal_message_does_not_trigger_safety_response() -> None:
    result = safety.detect("I have so much college work and I feel stressed")
    assert result.requires_safety_response is False


# ---------------------------------------------------------------------------
# Regression — duration phrases must not select goodbye (intent or semantic)
# ---------------------------------------------------------------------------
_DURATION_PHRASES = (
    "long time se",
    "for a long time",
    "long time",
    "bahut time se",
    "kaafi time se",
    "haan long time se",
)


def _is_goodbye_response(text: str) -> bool:
    for variants in INTENT_RESPONSES["goodbye"].values():
        if text in variants:
            return True
    return False


@pytest.mark.parametrize("phrase", _DURATION_PHRASES)
def test_duration_phrase_response_not_goodbye(phrase: str) -> None:
    from app.services.nlp.service import NLPService

    nlp = NLPService()
    nlp_result = nlp.classify(phrase)
    assert nlp_result.intent.label not in {"goodbye", "greeting"}

    ctx = _ctx(
        nlp_result.normalized_text,
        language=nlp_result.language,
        intent=nlp_result.intent.label,
        intent_confidence=nlp_result.intent.confidence_score,
        emotion=nlp_result.emotion.label,
        emotion_confidence=nlp_result.emotion.confidence_score,
    )
    out = selector.generate(ctx)
    assert not _is_goodbye_response(out.text)
    assert out.text


def test_kaafi_time_se_semantic_path_not_goodbye() -> None:
    """Unknown intent → semantic rung must still reject goodbye."""
    from app.services.nlp.service import NLPService

    nlp = NLPService()
    nlp_result = nlp.classify("kaafi time se")
    assert nlp_result.intent.label == "unknown"

    ctx = _ctx(
        nlp_result.normalized_text,
        language=nlp_result.language,
        intent=nlp_result.intent.label,
        intent_confidence=nlp_result.intent.confidence_score,
        emotion=nlp_result.emotion.label,
        emotion_confidence=nlp_result.emotion.confidence_score,
    )
    out = selector.generate(ctx)
    assert out.source in {"semantic", "fallback", "emotion"}
    assert not _is_goodbye_response(out.text)


def test_duration_after_emotional_context_not_goodbye() -> None:
    from app.services.nlp.service import NLPService

    nlp = NLPService()
    nlp_result = nlp.classify("long time se")
    recent = (
        "I have been feeling overwhelmed lately.",
        "I hear you. How long has it been feeling this way?",
        "long time se",
    )
    ctx = ResponseContext(
        message=nlp_result.normalized_text,
        language=nlp_result.language,
        intent=nlp_result.intent.label,
        intent_confidence=nlp_result.intent.confidence_score,
        emotion=nlp_result.emotion.label,
        emotion_confidence=nlp_result.emotion.confidence_score,
        recent_messages=recent,
    )
    out = selector.generate(ctx)
    assert not _is_goodbye_response(out.text)


@pytest.mark.parametrize("phrase", ("goodbye", "bye", "see you later"))
def test_explicit_farewell_still_selects_goodbye(phrase: str) -> None:
    from app.services.nlp.service import NLPService

    nlp = NLPService()
    nlp_result = nlp.classify(phrase)
    assert nlp_result.intent.label == "goodbye"
    ctx = _ctx(
        nlp_result.normalized_text,
        language=nlp_result.language,
        intent=nlp_result.intent.label,
        intent_confidence=nlp_result.intent.confidence_score,
        emotion=nlp_result.emotion.label,
        emotion_confidence=nlp_result.emotion.confidence_score,
    )
    out = selector.generate(ctx)
    assert _is_goodbye_response(out.text)


# ---------------------------------------------------------------------------
# Regression — moderate self_harm short-circuits Phase 6 fallback
# ---------------------------------------------------------------------------
_CRISIS_MARKERS = ("emergency", "safety", "trusted", "trust", "help", "right now")
_FALLBACK_HURT = FALLBACK_RESPONSES["en"][0]


def test_api_self_harm_want_to_hurt_self_returns_safety_response() -> None:
    resp = client.post("/api/chat", json={"message": "I want to hurt myself"})
    assert resp.status_code == 200
    data = resp.json()
    text = data["response"].lower()
    assert data["response"] != _FALLBACK_HURT
    assert "Tell me more about what's going on" not in data["response"]
    assert any(marker in text for marker in _CRISIS_MARKERS)
    _cleanup_conversation(data["conversation_id"])


def test_api_self_harm_thinking_about_hurting_returns_safety_response() -> None:
    resp = client.post(
        "/api/chat", json={"message": "I am thinking about hurting myself"}
    )
    assert resp.status_code == 200
    data = resp.json()
    text = data["response"].lower()
    assert data["response"] != _FALLBACK_HURT
    assert "Tell me more about what's going on" not in data["response"]
    assert any(marker in text for marker in _CRISIS_MARKERS)
    _cleanup_conversation(data["conversation_id"])


def test_api_normal_exam_stress_still_uses_phase6_response() -> None:
    assert safety.detect("I am stressed about my exams").requires_safety_response is False
    resp = client.post("/api/chat", json={"message": "I am stressed about my exams"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]
    text = data["response"].lower()
    assert "i'm an app, not an emergency" not in text
    assert "please reach out to emergency services" not in text
    assert data["response"] != _FALLBACK_HURT
    _cleanup_conversation(data["conversation_id"])


def test_api_safety_high_returns_crisis_reply() -> None:
    resp = client.post("/api/chat", json={"message": "I want to kill myself now"})
    assert resp.status_code == 200
    data = resp.json()
    text = data["response"].lower()
    assert "emergency" in text or "trust" in text or "app" in text
    # Must not be a casual greeting line.
    assert data["response"] not in INTENT_RESPONSES["greeting"]["en"]
    _cleanup_conversation(data["conversation_id"])


def test_api_normal_message_not_safety() -> None:
    resp = client.post(
        "/api/chat", json={"message": "I have a lot of homework stress"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "kill myself" not in data["response"].lower()
    _cleanup_conversation(data["conversation_id"])


# ---------------------------------------------------------------------------
# API / language / validation
# ---------------------------------------------------------------------------
def test_api_english_response() -> None:
    resp = client.post("/api/chat", json={"message": "hello there"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]
    assert data["conversation_id"]
    _cleanup_conversation(data["conversation_id"])


def test_api_hindi_response_language_routing() -> None:
    resp = client.post(
        "/api/chat", json={"message": "नमस्ते, मैं ठीक नहीं हूँ"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]
    _cleanup_conversation(data["conversation_id"])


def test_api_hinglish_response_language_routing() -> None:
    resp = client.post(
        "/api/chat", json={"message": "yaar exams ka pressure bahut zyada hai"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]
    _cleanup_conversation(data["conversation_id"])


def test_api_malformed_empty_message_rejected() -> None:
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={}).status_code == 422


def test_api_conversation_context_used() -> None:
    first = client.post("/api/chat", json={"message": "I am stressed about exams"})
    assert first.status_code == 200
    cid = first.json()["conversation_id"]
    second = client.post(
        "/api/chat",
        json={"message": "still stressed, cannot focus", "conversation_id": cid},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == cid
    assert second.json()["response"]
    _cleanup_conversation(cid)


def test_api_persistence_assistant_and_user_messages() -> None:
    from sqlalchemy import select

    resp = client.post("/api/chat", json={"message": "I feel lonely today"})
    assert resp.status_code == 200
    cid = resp.json()["conversation_id"]

    async def load() -> list[tuple[str, str]]:
        async with session_factory() as session:
            rows = await session.execute(
                select(Message).where(Message.conversation_id == uuid.UUID(cid))
            )
            return [(m.role, m.content) for m in rows.scalars().all()]

    rows = asyncio.run(load())
    contents = [content for _, content in rows]
    assert "I feel lonely today" in contents
    assert resp.json()["response"] in contents
    assert any(role == "user" for role, _ in rows)
    assert any(role == "assistant" for role, _ in rows)
    _cleanup_conversation(cid)


def test_api_nlp_failure_still_returns_reply(monkeypatch) -> None:
    from app.services.nlp.service import get_nlp_service_singleton

    nlp = get_nlp_service_singleton()

    def _raise(_text: str):
        raise NLPUnavailableError("model down")

    monkeypatch.setattr(nlp, "classify", _raise)
    resp = client.post("/api/chat", json={"message": "hello friend"})
    assert resp.status_code == 200
    assert resp.json()["response"]
    _cleanup_conversation(resp.json()["conversation_id"])


def test_api_version() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == "0.10.0-phase10"
    assert settings.version == "0.10.0-phase10"


def test_no_debug_fields_in_chat_response() -> None:
    resp = client.post("/api/chat", json={"message": "I am anxious about tomorrow"})
    assert resp.status_code == 200
    payload = resp.json()
    # Exact key set: no internal/debug fields may leak. `is_safety` is the
    # Phase 9 additive UI field, `suggest_exercise` the Phase 10 one.
    assert set(payload) == {
        "conversation_id",
        "message",
        "response",
        "is_safety",
        "suggest_exercise",
    }
    _cleanup_conversation(payload["conversation_id"])


def test_empty_text_error_contract() -> None:
    with pytest.raises(EmptyTextError):
        safety.detect("   ")


def test_generated_response_sources_are_closed() -> None:
    out = selector.generate(_ctx("hi", intent="greeting"))
    assert isinstance(out, GeneratedResponse)
    assert out.source in {"safety", "context", "intent", "emotion", "semantic", "fallback"}


def test_classification_result_shapes_for_context() -> None:
    """Selector consumes the same field shapes NLPService.classify returns."""
    result = ClassificationResult(
        language="en",
        original_text="I feel sad",
        normalized_text="i feel sad",
        intent=IntentResult(label="sadness", confidence_score=0.9, alternatives=()),
        emotion=EmotionResult(label="sadness", confidence_score=0.8, alternatives=()),
        processing_time_ms=1.0,
    )
    out = selector.generate(
        _ctx(
            result.original_text,
            language=result.language,
            intent=result.intent.label,
            intent_confidence=result.intent.confidence_score,
            emotion=result.emotion.label,
            emotion_confidence=result.emotion.confidence_score,
        )
    )
    assert out.text in INTENT_RESPONSES["sadness"]["en"]
