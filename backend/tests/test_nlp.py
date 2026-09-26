"""Phase 3A NLP tests.

Covers: normalization, language detection (en/hi/hinglish), embedding
service, NLPService, and /api/nlp/analyze. All inputs are synthetic — no
real people's conversations.

Embedding tests load the local multilingual model once (CPU-only). First
run may download the model; subsequent runs use the Hugging Face cache.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.errors import EmptyTextError
from app.services.nlp import (
    NLPService,
    detect_language,
    get_embedding_service,
    normalize_text,
)

client = TestClient(app)

ENGLISH = "I have been feeling lonely lately."
HINDI = "मुझे आज बहुत अकेला महसूस हो रहा है।"
HINGLISH = "Mujhe aajkal bahut lonely feel hota hai."


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
def test_normalize_collapses_whitespace() -> None:
    assert normalize_text("   I   feel    stressed   ") == "i feel stressed"


def test_normalize_preserves_negation() -> None:
    out = normalize_text("I am not feeling sad.")
    assert "not" in out
    assert "sad" in out


def test_normalize_preserves_hindi() -> None:
    out = normalize_text("  मुझे   अकेला  लगता है  ")
    assert "अकेला" in out
    assert "  " not in out  # whitespace collapsed


def test_normalize_empty() -> None:
    assert normalize_text("") == ""
    assert normalize_text("     ") == ""


def test_normalize_mixed_punctuation() -> None:
    out = normalize_text("Why am I feeling like this?!")
    assert out == "why am i feeling like this?!"


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
def test_detect_english() -> None:
    assert detect_language(ENGLISH) == "en"


def test_detect_hindi_devanagari() -> None:
    assert detect_language(HINDI) == "hi"


def test_detect_hinglish() -> None:
    assert detect_language(HINGLISH) == "hinglish"


def test_detect_hinglish_example2() -> None:
    assert (
        detect_language("Yaar mujhe kuch bhi karne ka mann nahi karta.") == "hinglish"
    )


def test_detect_hinglish_kaafi_and_haan() -> None:
    assert detect_language("kaafi time se") == "hinglish"
    assert detect_language("haan long time se") == "hinglish"


def test_detect_duration_phrases_english() -> None:
    assert detect_language("long time se") == "en"
    assert detect_language("for a long time") == "en"


def test_detect_empty_unknown() -> None:
    assert detect_language("") == "unknown"
    assert detect_language("   ") == "unknown"


def test_detect_negation_english_stays_english() -> None:
    assert detect_language("I am not feeling sad.") == "en"


# ---------------------------------------------------------------------------
# Embedding service
# ---------------------------------------------------------------------------
def test_embedding_service_dimension() -> None:
    svc = get_embedding_service()
    vec = svc.encode("hello world")
    # paraphrase-multilingual-MiniLM-L12-v2 → 384
    assert vec.shape == (384,)
    assert svc.dimension == 384
    assert vec.dtype.name == "float32" or str(vec.dtype) == "float32"


def test_embedding_batch() -> None:
    svc = get_embedding_service()
    vecs = svc.encode_batch(["hello", "namaste"])
    assert len(vecs) == 2
    assert all(v.shape == (384,) for v in vecs)


def test_embedding_normalized() -> None:
    import math

    svc = get_embedding_service()
    vec = svc.encode("hello")
    norm = math.sqrt(float(sum(float(x) * float(x) for x in vec)))
    assert abs(norm - 1.0) < 1e-3


def test_embedding_cpu_device() -> None:
    svc = get_embedding_service()
    assert svc.device == "cpu"
    assert svc.is_loaded


# ---------------------------------------------------------------------------
# NLPService
# ---------------------------------------------------------------------------
def test_nlp_service_process_english() -> None:
    result = NLPService().process(ENGLISH)
    assert result.language == "en"
    assert result.original_text == ENGLISH
    assert result.normalized_text == ENGLISH.lower()
    assert result.embedding_dimension == 384
    assert result.processing_time_ms >= 0


def test_nlp_service_process_hinglish() -> None:
    result = NLPService().process(HINGLISH)
    assert result.language == "hinglish"
    assert result.embedding_dimension == 384


def test_nlp_service_process_hindi() -> None:
    result = NLPService().process(HINDI)
    assert result.language == "hi"
    assert result.embedding_dimension == 384


def test_nlp_service_empty_raises() -> None:
    with pytest.raises(EmptyTextError):
        NLPService().process("")
    with pytest.raises(EmptyTextError):
        NLPService().process("     ")


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------
def test_nlp_analyze_endpoint_english() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": ENGLISH})
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "en"
    assert data["embedding_dimension"] == 384
    assert "embedding" not in data  # vector never exposed
    assert data["processing_time_ms"] >= 0


def test_nlp_analyze_endpoint_hinglish() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": HINGLISH})
    assert resp.status_code == 200
    assert resp.json()["language"] == "hinglish"


def test_nlp_analyze_endpoint_hindi() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": HINDI})
    assert resp.status_code == 200
    assert resp.json()["language"] == "hi"


def test_nlp_analyze_endpoint_empty_422() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": ""})
    assert resp.status_code == 422


def test_nlp_analyze_endpoint_whitespace_422() -> None:
    resp = client.post("/api/nlp/analyze", json={"text": "     "})
    assert resp.status_code == 422


def test_nlp_analyze_endpoint_missing_field_422() -> None:
    resp = client.post("/api/nlp/analyze", json={})
    assert resp.status_code == 422


def test_nlp_analyze_long_valid_message() -> None:
    long_text = (
        "I have been feeling quite stressed about my exams and I cannot sleep "
        "properly at night. Sometimes I worry too much about the future."
    )
    resp = client.post("/api/nlp/analyze", json={"text": long_text})
    assert resp.status_code == 200
    assert resp.json()["language"] == "en"


def test_chat_api_still_works_after_nlp() -> None:
    """Existing chat endpoint remains independent of NLP success."""
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json()["response"]
    # cleanup
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
