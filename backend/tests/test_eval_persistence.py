"""Phase 7 database / persistence evaluation extras."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.connection import session_factory
from app.main import app
from app.models import Conversation, Message

client = TestClient(app)


def _cleanup(cid: str) -> None:
    if session_factory is None:
        return

    async def run() -> None:
        async with session_factory() as session:
            conversation = await session.get(Conversation, uuid.UUID(cid))
            if conversation is not None:
                await session.delete(conversation)
                await session.commit()

    asyncio.run(run())


def test_message_ordering_user_then_assistant() -> None:
    resp = client.post("/api/chat", json={"message": "ordering probe one"})
    assert resp.status_code == 200
    cid = resp.json()["conversation_id"]
    resp2 = client.post(
        "/api/chat",
        json={"message": "ordering probe two", "conversation_id": cid},
    )
    assert resp2.status_code == 200

    async def load():
        async with session_factory() as session:
            rows = await session.execute(
                select(Message)
                .where(Message.conversation_id == uuid.UUID(cid))
                .order_by(Message.created_at)
            )
            return [(m.role, m.content) for m in rows.scalars().all()]

    rows = asyncio.run(load())
    roles = [r for r, _ in rows]
    # alternating user/assistant
    assert roles[0] == "user"
    assert roles[1] == "assistant"
    assert roles[2] == "user"
    assert roles[3] == "assistant"
    contents = [c for _, c in rows]
    assert contents.count("ordering probe one") == 1
    assert contents.count("ordering probe two") == 1
    _cleanup(cid)


def test_repeated_identical_send_not_duplicated_in_one_request() -> None:
    """One HTTP request → exactly one user + one assistant message."""
    resp = client.post("/api/chat", json={"message": "duplicate probe"})
    assert resp.status_code == 200
    cid = resp.json()["conversation_id"]

    async def count():
        async with session_factory() as session:
            rows = await session.execute(
                select(Message).where(Message.conversation_id == uuid.UUID(cid))
            )
            return list(rows.scalars().all())

    msgs = asyncio.run(count())
    assert len(msgs) == 2
    _cleanup(cid)


def test_failed_request_does_not_orphan_partial_user_only_message_for_404() -> None:
    """ConversationNotFound is raised before user message create? Check order.

    ChatService creates conversation only when conversation_id is None;
    when id is provided and missing, raises before message create.
    """
    resp = client.post(
        "/api/chat",
        json={
            "message": "should not persist",
            "conversation_id": "00000000-0000-0000-0000-000000000042",
        },
    )
    assert resp.status_code == 404

    async def find():
        async with session_factory() as session:
            rows = await session.execute(
                select(Message).where(
                    Message.content == "should not persist"
                )
            )
            return list(rows.scalars().all())

    assert asyncio.run(find()) == []
