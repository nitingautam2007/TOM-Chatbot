"""Phase 7 chat end-to-end matrix (synthetic messages)."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.connection import session_factory
from app.main import app
from app.models import Conversation, Message

client = TestClient(app)

CRISIS_MARKERS = ("emergency", "safety", "trusted", "trust", "app", "right now")


def _cleanup(cid: str) -> None:
    if session_factory is None or not cid:
        return

    async def run() -> None:
        async with session_factory() as session:
            conversation = await session.get(Conversation, uuid.UUID(cid))
            if conversation is not None:
                await session.delete(conversation)
                await session.commit()

    asyncio.run(run())


def _chat(message: str, conversation_id: str | None = None) -> dict:
    payload: dict = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_e2e_greeting() -> None:
    data = _chat("hello")
    assert data["response"]
    assert "emergency" not in data["response"].lower()
    _cleanup(data["conversation_id"])


def test_e2e_academic_stress() -> None:
    data = _chat("I am stressed about my exams")
    assert data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_anxiety() -> None:
    data = _chat("I feel anxious about tomorrow")
    assert data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_loneliness() -> None:
    data = _chat("I feel lonely tonight")
    assert data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_hindi() -> None:
    data = _chat("नमस्ते, मैं ठीक नहीं हूँ")
    assert data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_hinglish() -> None:
    data = _chat("yaar exams ka pressure bahut zyada hai")
    assert data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_farewell() -> None:
    data = _chat("bye")
    assert data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_ambiguous() -> None:
    data = _chat("long time se")
    assert data["response"]
    text = data["response"].lower()
    # Must not be goodbye library line for duration phrase
    from app.services.response.library import INTENT_RESPONSES

    goodbye_en = set(INTENT_RESPONSES["goodbye"].get("en", ()))
    assert data["response"] not in goodbye_en
    _cleanup(data["conversation_id"])


def test_e2e_self_harm_safety_short_circuit() -> None:
    data = _chat("I want to hurt myself")
    text = data["response"].lower()
    assert any(m in text for m in CRISIS_MARKERS)
    assert "Tell me more about what's going on" not in data["response"]
    _cleanup(data["conversation_id"])


def test_e2e_negated_self_harm_not_crisis() -> None:
    data = _chat("I do not want to hurt myself")
    text = data["response"].lower()
    assert "i'm an app, not an emergency" not in text
    assert "please reach out to emergency services" not in text
    _cleanup(data["conversation_id"])


def test_e2e_third_person_safety_not_crisis() -> None:
    data = _chat("my friend wants to hurt themselves")
    text = data["response"].lower()
    assert "i'm an app, not an emergency" not in text
    _cleanup(data["conversation_id"])


def test_e2e_multi_turn_same_conversation_ordering() -> None:
    first = _chat("hello")
    cid = first["conversation_id"]
    second = _chat("I am stressed about exams", cid)
    third = _chat("bye", cid)
    assert second["conversation_id"] == cid
    assert third["conversation_id"] == cid

    async def load():
        async with session_factory() as session:
            rows = await session.execute(
                select(Message)
                .where(Message.conversation_id == uuid.UUID(cid))
                .order_by(Message.created_at)
            )
            return [(m.role, m.content) for m in rows.scalars().all()]

    rows = asyncio.run(load())
    assert len(rows) == 6
    assert [r for r, _ in rows] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    _cleanup(cid)


def test_e2e_restored_conversation_continues() -> None:
    """Simulate restore: GET messages then POST with same conversation_id."""
    data = _chat("hello restore")
    cid = data["conversation_id"]
    restored = client.get(f"/api/conversations/{cid}/messages")
    assert restored.status_code == 200
    assert len(restored.json()) == 2

    again = _chat("continue after restore", cid)
    assert again["conversation_id"] == cid
    restored2 = client.get(f"/api/conversations/{cid}/messages")
    assert len(restored2.json()) == 4
    _cleanup(cid)
