"""Phase 7 performance measurements — local CPU-only latencies.

Records timings for report; soft assertions only (no premature optimization).
"""

from __future__ import annotations

import statistics
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.nlp.service import NLPService
from app.services.response.selector import ResponseSelector
from app.services.response.types import ResponseContext
from app.services.safety.service import SafetyService

client = TestClient(app)


def _ms(samples: list[float]) -> dict[str, float]:
    return {
        "n": len(samples),
        "median_ms": round(statistics.median(samples), 2),
        "p95_ms": round(sorted(samples)[max(0, int(len(samples) * 0.95) - 1)], 2),
        "max_ms": round(max(samples), 2),
    }


def test_performance_measurements(capsys) -> None:
    safety = SafetyService()
    nlp = NLPService()
    selector = ResponseSelector()

    # First-ever load may include HF model download (~minutes on cold cache).
    # Report that separately; warm-path assert below is what matters on CPU.
    t_dl = time.perf_counter()
    nlp.classify("warm model cache")
    model_load_ms = (time.perf_counter() - t_dl) * 1000

    t0 = time.perf_counter()
    nlp.classify("cold start hello world")
    cold_ms = (time.perf_counter() - t0) * 1000

    # Warm NLP classify
    classify_samples = []
    for i in range(20):
        t = time.perf_counter()
        nlp.classify(f"I am feeling stressed about item {i}")
        classify_samples.append((time.perf_counter() - t) * 1000)

    safety_samples = []
    for i in range(50):
        t = time.perf_counter()
        safety.detect("I am stressed about my exams and cannot focus")
        safety_samples.append((time.perf_counter() - t) * 1000)

    # Response selection (semantic index may build on first hit)
    r = nlp.classify("hello there")
    ctx = ResponseContext(
        message="hello there",
        language=r.language,
        intent=r.intent.label,
        intent_confidence=r.intent.confidence_score,
        emotion=r.emotion.label,
        emotion_confidence=r.emotion.confidence_score,
        recent_messages=(),
    )
    selector.generate(ctx)  # warm
    resp_samples = []
    for i in range(20):
        t = time.perf_counter()
        selector.generate(ctx)
        resp_samples.append((time.perf_counter() - t) * 1000)

    # Chat endpoint (includes persistence)
    chat_samples = []
    for i in range(10):
        t = time.perf_counter()
        resp = client.post("/api/chat", json={"message": f"performance probe {i}"})
        chat_samples.append((time.perf_counter() - t) * 1000)
        assert resp.status_code == 200
        cid = resp.json()["conversation_id"]
        # cleanup
        import asyncio
        import uuid

        from app.database.connection import session_factory
        from app.models import Conversation

        async def _cleanup(conversation_id: str) -> None:
            if session_factory is None:
                return
            async with session_factory() as session:
                conversation = await session.get(Conversation, uuid.UUID(conversation_id))
                if conversation is not None:
                    await session.delete(conversation)
                    await session.commit()

        asyncio.run(_cleanup(cid))

    report = {
        "model_load_ms": round(model_load_ms, 2),
        "warm_after_load_nlp_ms": round(cold_ms, 2),
        "warm_nlp_classify": _ms(classify_samples),
        "safety_detect": _ms(safety_samples),
        "response_selection": _ms(resp_samples),
        "chat_endpoint": _ms(chat_samples),
    }
    with capsys.disabled():
        print("\nPERFORMANCE:", report)

    # Generous ceilings for i3/8GB CPU-only — catch pathological regressions only.
    # model_load may be slow on first HF download; not gated.
    assert report["warm_after_load_nlp_ms"] < 5_000
    assert report["warm_nlp_classify"]["median_ms"] < 5_000
    assert report["safety_detect"]["median_ms"] < 500
    assert report["response_selection"]["median_ms"] < 5_000
    assert report["chat_endpoint"]["median_ms"] < 30_000
