"""Phase 10 — exercise-suggestion flag + safety regression.

Each test maps to a Phase 10 guarantee:
  * suggest_exercise is an additive ChatResponse field (exact key set pinned
    in tests/test_response.py::test_no_debug_fields_in_chat_response)
  * safety replies NEVER carry an exercise suggestion
  * normal stress/anxiety/coping/academic conversations DO
  * greeting/positive conversations do not
  * the strategy→suggestion mapping cannot silently widen
  * GeneratedResponse.strategy mirrors the strategy actually used
"""

import uuid
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.database.connection import session_factory
from app.main import app
from app.services.chat_service import _EXERCISE_STRATEGIES
from app.services.response.selector import ResponseSelector
from app.services.response.types import ResponseContext

client = TestClient(app)
selector = ResponseSelector()


def _cleanup_conversation(conversation_id: str) -> None:
    if session_factory is None or not conversation_id:
        return

    async def run() -> None:
        async with session_factory() as session:
            from app.models import Conversation

            conversation = await session.get(Conversation, uuid.UUID(conversation_id))
            if conversation is not None:
                await session.delete(conversation)
                await session.commit()

    asyncio.run(run())


def _ctx(message: str, **kw) -> ResponseContext:
    kw.setdefault("language", "en")
    kw.setdefault("intent_confidence", 1.0)
    kw.setdefault("emotion_confidence", 1.0)
    return ResponseContext(message=message, **kw)


# ------------------------------------------------------- safety never suggests


@pytest.mark.parametrize(
    "message",
    [
        "I want to hurt myself",
        "I am thinking about hurting myself",
        "I am happy today but I want to hurt myself",
    ],
)
def test_safety_reply_never_suggests_exercise(message: str) -> None:
    resp = client.post("/api/chat", json={"message": message})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_safety"] is True
    assert data["suggest_exercise"] is False
    _cleanup_conversation(data["conversation_id"])


# ------------------------------------------------------------- normal suggests


def test_stress_conversation_suggests_exercise() -> None:
    resp = client.post("/api/chat", json={"message": "I am stressed about my exams"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_safety"] is False
    assert data["suggest_exercise"] is True
    _cleanup_conversation(data["conversation_id"])


def test_greeting_does_not_suggest_exercise() -> None:
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_safety"] is False
    assert data["suggest_exercise"] is False
    _cleanup_conversation(data["conversation_id"])


# ------------------------------------------------------------ mapping is closed


def test_exercise_strategies_are_exactly_the_stress_family() -> None:
    """The flag must not silently widen to unrelated strategies."""
    assert _EXERCISE_STRATEGIES == {
        "stress_support",
        "anxiety_support",
        "coping_support",
        "academic_support",
    }


@pytest.mark.parametrize(
    "intent,emotion",
    [
        ("stress", "stress"),
        ("anxiety", "anxiety"),
        ("coping_help", "neutral"),
        ("academic_pressure", "stress"),
    ],
)
def test_stress_family_strategies_are_exposed(intent: str, emotion: str) -> None:
    out = selector.generate(
        _ctx("I am overwhelmed", intent=intent, emotion=emotion)
    )
    assert out.strategy in _EXERCISE_STRATEGIES


@pytest.mark.parametrize(
    "intent,emotion",
    [
        ("greeting", "neutral"),
        ("goodbye", "neutral"),
        ("general_conversation", "happiness"),
    ],
)
def test_non_stress_strategies_are_not_exposed(intent: str, emotion: str) -> None:
    out = selector.generate(
        _ctx("hello there", intent=intent, emotion=emotion)
    )
    assert out.strategy not in _EXERCISE_STRATEGIES
