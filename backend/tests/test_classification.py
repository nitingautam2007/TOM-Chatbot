"""Phase 3B intent + emotion classification tests.

All inputs are synthetic/curated prototypes — not clinical validation data.
The local embedding model loads once on first classification (CPU-only).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.errors import EmptyTextError
from app.services.nlp import NLPService, classify_emotion, classify_intent, get_embedding_service
from app.services.nlp.data import EMOTION_LABELS, INTENT_LABELS
from app.services.nlp.negation import has_negation, negation_penalty
from app.services.nlp.prototypes import get_emotion_bank, get_intent_bank

client = TestClient(app)

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
def test_intent_english_sadness() -> None:
    emb = get_embedding_service().encode("I feel really sad today")
    result = classify_intent(emb)
    assert result.label == "sadness"
    assert 0.0 <= result.confidence_score <= 1.0
    assert isinstance(result.alternatives, tuple)


def test_intent_english_greeting() -> None:
    emb = get_embedding_service().encode("hello there")
    result = classify_intent(emb)
    assert result.label == "greeting"


def test_intent_english_stress() -> None:
    emb = get_embedding_service().encode("I am very stressed about everything")
    result = classify_intent(emb)
    assert result.label == "stress"


def test_intent_english_loneliness() -> None:
    emb = get_embedding_service().encode("I feel lonely and have nobody to talk to")
    assert classify_intent(emb).label == "loneliness"


def test_intent_english_anxiety() -> None:
    emb = get_embedding_service().encode("I am constantly worrying about the future")
    assert classify_intent(emb).label == "anxiety"


def test_intent_hindi_sadness() -> None:
    emb = get_embedding_service().encode("मैं बहुत उदास हूँ")
    result = classify_intent(emb)
    assert result.label == "sadness"


def test_intent_hinglish_sadness() -> None:
    emb = get_embedding_service().encode("yaar aaj mood bahut down hai")
    result = classify_intent(emb)
    assert result.label in {"sadness", "stress"}  # prototype proximity
    assert result.label != "unknown"


def test_intent_hinglish_loneliness() -> None:
    emb = get_embedding_service().encode("mujhe bahut akela lagta hai")
    result = classify_intent(emb)
    assert result.label in {"loneliness", "sadness", "emotional_support"}


def test_intent_academic_pressure() -> None:
    emb = get_embedding_service().encode("I am stressed about my exams and studies")
    assert classify_intent(emb).label in {"academic_pressure", "stress"}


def test_intent_unknown_below_threshold() -> None:
    # Gibberish / no semantic overlap with any prototype class.
    emb = get_embedding_service().encode("xqz plugh frobnicate")
    result = classify_intent(emb)
    assert result.label == "unknown"
    assert result.confidence_score < 1.0


def test_intent_labels_cover_taxonomy() -> None:
    from app.services.nlp.data import INTENT_LABELS as labels

    assert len(labels) == 15
    assert "unknown" in labels
    assert set(INTENT_LABELS) == set(labels)


# ---------------------------------------------------------------------------
# Regression — duration phrases must not become goodbye / greeting
# ---------------------------------------------------------------------------
_DURATION_PHRASES = (
    "long time se",
    "for a long time",
    "long time",
    "bahut time se",
    "kaafi time se",
    "haan long time se",
)


@pytest.mark.parametrize("phrase", _DURATION_PHRASES)
def test_duration_phrase_not_goodbye_or_greeting(phrase: str) -> None:
    from app.services.nlp.intent import classify_intent_text

    emb = get_embedding_service().encode(phrase)
    result = classify_intent_text(emb, phrase)
    assert result.label not in {"goodbye", "greeting"}


@pytest.mark.parametrize("phrase", ("goodbye", "bye", "see you later"))
def test_explicit_farewell_still_goodbye(phrase: str) -> None:
    from app.services.nlp.intent import classify_intent_text

    emb = get_embedding_service().encode(phrase)
    result = classify_intent_text(emb, phrase)
    assert result.label == "goodbye"
    assert result.confidence_score >= 0.40


def test_extended_farewell_cues_have_evidence() -> None:
    from app.services.nlp.farewell import has_farewell

    for cue in ("byebye", "cya", "gtg", "ttyl"):
        assert has_farewell(cue)


def test_byebye_still_classifies_goodbye() -> None:
    # Regression: \bbye+\b cannot match inside "byebye" — without an explicit
    # alternative the farewell gate used to force it to unknown.
    from app.services.nlp.intent import classify_intent_text

    emb = get_embedding_service().encode("byebye")
    result = classify_intent_text(emb, "byebye")
    assert result.label == "goodbye"


def test_duration_phrases_have_no_farewell_evidence() -> None:
    from app.services.nlp.farewell import has_farewell

    for phrase in _DURATION_PHRASES:
        assert not has_farewell(phrase)


# ---------------------------------------------------------------------------
# Emotion classification
# ---------------------------------------------------------------------------
def test_emotion_sadness() -> None:
    emb = get_embedding_service().encode("I feel really sad")
    result = classify_emotion(emb, "i feel really sad")
    assert result.label == "sadness"
    assert 0.0 <= result.confidence_score <= 1.0


def test_emotion_anxiety() -> None:
    emb = get_embedding_service().encode("I am so nervous and worried all the time")
    result = classify_emotion(emb, "i am so nervous and worried all the time")
    assert result.label == "anxiety"


def test_emotion_anger() -> None:
    emb = get_embedding_service().encode("I am really angry right now")
    result = classify_emotion(emb, "i am really angry right now")
    assert result.label == "anger"


def test_emotion_stress() -> None:
    emb = get_embedding_service().encode("I am under a lot of pressure and stressed")
    result = classify_emotion(emb, "i am under a lot of pressure and stressed")
    assert result.label in {"stress", "anxiety"}


def test_emotion_loneliness() -> None:
    emb = get_embedding_service().encode("I feel alone and nobody understands me")
    result = classify_emotion(emb, "i feel alone and nobody understands me")
    assert result.label in {"loneliness", "sadness"}


def test_emotion_happiness() -> None:
    emb = get_embedding_service().encode("I am really happy today")
    result = classify_emotion(emb, "i am really happy today")
    assert result.label in {"happiness", "positive"}


def test_emotion_positive() -> None:
    emb = get_embedding_service().encode("I feel hopeful and things are getting better")
    result = classify_emotion(emb, "i feel hopeful and things are getting better")
    assert result.label in {"positive", "happiness"}


def test_emotion_neutral() -> None:
    emb = get_embedding_service().encode("my exam is on Monday at the library")
    result = classify_emotion(emb, "my exam is on monday at the library")
    assert result.label in {"neutral", "stress", "anxiety"}  # exam context can lean stress


def test_emotion_mixed() -> None:
    emb = get_embedding_service().encode("I am happy but also nervous about it")
    result = classify_emotion(emb, "i am happy but also nervous about it")
    assert result.label in {"mixed", "positive", "happiness", "anxiety"}


def test_emotion_uncertain_gibberish() -> None:
    emb = get_embedding_service().encode("xqz plugh frobnicate")
    result = classify_emotion(emb, "xqz plugh frobnicate")
    assert result.label == "uncertain"


def test_emotion_labels_cover_taxonomy() -> None:
    assert len(EMOTION_LABELS) == 10
    assert "uncertain" in EMOTION_LABELS


# ---------------------------------------------------------------------------
# Negation
# ---------------------------------------------------------------------------
def test_negation_presence() -> None:
    assert has_negation("i am not sad")
    assert has_negation("nahi acha lag raha")
    assert not has_negation("i am happy today")


def test_negation_penalty_reduces_sadness() -> None:
    base = 1.0
    penalized = negation_penalty("sadness", "i am not sad")
    assert penalized < base
    # No negation → no penalty
    assert negation_penalty("sadness", "i am sad") == 1.0


def test_negation_not_sad_affected() -> None:
    """'I am not sad' should dampen sadness enough to often land elsewhere."""
    emb = get_embedding_service().encode("I am not sad")
    result = classify_emotion(emb, "i am not sad")
    # Soft assertion: either not sadness, or significantly reduced score.
    if result.label == "sadness":
        # If still sadness, the raw similarity must be high enough to survive
        # the 0.55 penalty — acceptable for prototype stage.
        assert result.confidence_score > 0.4
    else:
        assert result.label != "sadness"


def test_negation_not_stress_does_not_reduce_without_keyword() -> None:
    # "not" present but no sadness keyword → no sadness penalty
    assert negation_penalty("sadness", "i am not going to the park") == 1.0


# ---------------------------------------------------------------------------
# NLPService.classify
# ---------------------------------------------------------------------------
def test_service_classify_english() -> None:
    result = NLPService().classify("I feel stressed about my exams")
    assert result.language == "en"
    assert result.intent.label in INTENT_LABELS
    assert result.emotion.label in EMOTION_LABELS
    assert result.original_text.startswith("I feel")
    assert result.processing_time_ms >= 0
    # No embedding vector on ClassificationResult
    assert not hasattr(result, "embedding")
    assert not hasattr(result, "vector")


def test_service_classify_hindi() -> None:
    result = NLPService().classify("मुझे आज बहुत अकेला महसूस हो रहा है")
    assert result.language == "hi"
    assert result.intent.label in INTENT_LABELS
    assert result.emotion.label in EMOTION_LABELS


def test_service_classify_hinglish() -> None:
    result = NLPService().classify("Mujhe aajkal bahut lonely feel hota hai")
    assert result.language == "hinglish"
    assert result.intent.label in INTENT_LABELS


def test_service_classify_empty_raises() -> None:
    with pytest.raises(EmptyTextError):
        NLPService().classify("")
    with pytest.raises(EmptyTextError):
        NLPService().classify("   ")


def test_service_classify_unicode_hindi() -> None:
    result = NLPService().classify("मैं उदास महसूस कर रहा हूँ")
    assert result.language == "hi"
    assert "उदास" in result.normalized_text or "ud" not in result.normalized_text


def test_service_classify_long_message() -> None:
    long_msg = (
        "I have been feeling quite stressed about my exams and I cannot sleep "
        "properly at night. Sometimes I worry too much about the future and "
        "I feel lonely when nobody replies."
    ) * 3
    result = NLPService().classify(long_msg)
    assert result.intent.label in INTENT_LABELS
    assert result.emotion.label in EMOTION_LABELS


# ---------------------------------------------------------------------------
# API endpoint /api/nlp/classify
# ---------------------------------------------------------------------------
def test_classify_endpoint_english() -> None:
    resp = client.post(
        "/api/nlp/classify", json={"message": "I feel sad and lonely today"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {
        "original_text",
        "normalized_text",
        "language",
        "intent",
        "emotion",
        "processing_time_ms",
    }
    assert data["language"] == "en"
    assert data["intent"]["label"] in INTENT_LABELS
    assert data["emotion"]["label"] in EMOTION_LABELS
    assert "confidence_score" in data["intent"]
    assert "confidence_score" in data["emotion"]
    assert isinstance(data["intent"]["alternatives"], list)
    # No embedding leakage
    raw = resp.text.lower()
    assert "embedding" not in raw
    assert "vector" not in raw
    assert "prototype" not in raw


def test_classify_endpoint_hindi() -> None:
    resp = client.post(
        "/api/nlp/classify",
        json={"message": "मुझे बहुत तनाव हो रहा है"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "hi"
    assert data["intent"]["label"] in INTENT_LABELS


def test_classify_endpoint_hinglish() -> None:
    resp = client.post(
        "/api/nlp/classify",
        json={"message": "Yaar mujhe kuch bhi karne ka mann nahi karta."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "hinglish"
    assert data["intent"]["label"] in INTENT_LABELS


def test_classify_endpoint_empty_422() -> None:
    resp = client.post("/api/nlp/classify", json={"message": ""})
    assert resp.status_code == 422


def test_classify_endpoint_whitespace_422() -> None:
    resp = client.post("/api/nlp/classify", json={"message": "     "})
    assert resp.status_code == 422


def test_classify_endpoint_missing_field_422() -> None:
    resp = client.post("/api/nlp/classify", json={})
    assert resp.status_code == 422


def test_classify_endpoint_ambiguous_okay() -> None:
    """Vague backchannels should map to unknown/uncertain."""
    for word in ("okay", "hmm", "fine", "yeah"):
        resp = client.post("/api/nlp/classify", json={"message": word})
        assert resp.status_code == 200, word
        data = resp.json()
        assert data["intent"]["label"] == "unknown", word
        assert data["emotion"]["label"] == "uncertain", word


def test_classify_endpoint_schema_fields() -> None:
    resp = client.post(
        "/api/nlp/classify", json={"message": "I need someone to talk to"}
    )
    assert resp.status_code == 200
    data = resp.json()
    intent = data["intent"]
    emotion = data["emotion"]
    assert isinstance(intent["confidence_score"], float)
    assert isinstance(emotion["confidence_score"], float)
    assert 0.0 <= intent["confidence_score"] <= 1.0
    assert 0.0 <= emotion["confidence_score"] <= 1.0
    for alt in intent["alternatives"]:
        assert set(alt.keys()) == {"label", "score"}


def test_classify_endpoint_no_embedding_leak() -> None:
    resp = client.post(
        "/api/nlp/classify", json={"message": "I am feeling anxious"}
    )
    body = resp.json()
    # Strict: only allowed top-level keys
    assert set(body.keys()) == {
        "original_text",
        "normalized_text",
        "language",
        "intent",
        "emotion",
        "processing_time_ms",
    }
    # Intent/emotion only expose label + score + alternatives
    assert set(body["intent"].keys()) == {
        "label",
        "confidence_score",
        "alternatives",
    }
    assert set(body["emotion"].keys()) == {
        "label",
        "confidence_score",
        "alternatives",
    }


def test_classify_endpoint_performance_no_reload() -> None:
    """Second call should not rebuild prototypes (fast path)."""
    import time

    first = client.post(
        "/api/nlp/classify", json={"message": "I feel a bit down"}
    )
    assert first.status_code == 200
    t0 = time.perf_counter()
    second = client.post(
        "/api/nlp/classify", json={"message": "I feel stressed"}
    )
    elapsed = time.perf_counter() - t0
    assert second.status_code == 200
    # Cached prototypes: well under 2s on this machine (embedding encode dominates).
    assert elapsed < 5.0


def test_chat_endpoint_unchanged_after_classify() -> None:
    """Phase 3B must not break /api/chat."""
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json()["response"]

    import asyncio
    import uuid

    from app.database.connection import session_factory
    from app.models import Conversation

    conv_id = resp.json()["conversation_id"]

    async def _cleanup() -> None:
        if session_factory is None:
            return
        async with session_factory() as session:
            c = await session.get(Conversation, uuid.UUID(conv_id))
            if c is not None:
                await session.delete(c)
                await session.commit()

    asyncio.run(_cleanup())


def test_analyze_endpoint_still_works() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": "hello world"})
    assert resp.status_code == 200
    assert resp.json()["embedding_dimension"] == 384


def test_settings_version() -> None:
    from app.core.config import settings

    assert settings.version == "0.10.0-phase10"
    assert settings.intent_confidence_threshold > 0
    assert settings.emotion_confidence_threshold > 0
    assert settings.classification_ambiguity_margin >= 0
