"""Phase 2 database tests.

These tests run against the configured TOM_DATABASE_URL (the existing
tom_chatbot development database). They only insert rows they create and
always delete those rows afterwards — no pre-existing data is modified.
If the database is not configured, they skip with a setup hint.
"""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.connection import db_not_configured_message, engine, session_factory
from app.main import app
from app.models import Conversation, Message, User
from app.repositories import ConversationRepository, MessageRepository, UserRepository

client = TestClient(app)


def test_database_configuration() -> None:
    """TOM_DATABASE_URL loaded from backend/.env in async SQLAlchemy format."""
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert engine is not None
    assert session_factory is not None


def _require_db() -> None:
    if session_factory is None:
        pytest.skip(db_not_configured_message())


async def _delete_conversation(conversation_id: uuid.UUID) -> None:
    async with session_factory() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is not None:
            await session.delete(conversation)
            await session.commit()


async def _delete_user(user_id: uuid.UUID) -> None:
    async with session_factory() as session:
        user = await session.get(User, user_id)
        if user is not None:
            await session.delete(user)
            await session.commit()


def test_database_connection() -> None:
    _require_db()

    async def run() -> None:
        async with engine.connect() as conn:
            result = await conn.exec_driver_sql("SELECT 1")
            assert result.scalar() == 1

    asyncio.run(run())


def test_user_creation() -> None:
    _require_db()

    async def run() -> None:
        async with session_factory() as session:
            user = User(id=uuid.uuid4())
            session.add(user)
            await session.commit()
            user_id = user.id

        async with session_factory() as session:
            fetched = await UserRepository(session).get_by_id(user_id)
            assert fetched is not None
            assert fetched.id == user_id
            assert fetched.created_at is not None
            assert fetched.created_at.tzinfo is not None  # UTC tz-aware

        await _delete_user(user_id)

    asyncio.run(run())


def test_conversation_creation() -> None:
    _require_db()

    async def run() -> None:
        async with session_factory() as session:
            user = User(id=uuid.uuid4())
            session.add(user)
            await session.flush()
            conversation = await ConversationRepository(session).create(
                user.id, "unit test conversation"
            )
            await session.commit()
            conversation_id = conversation.id
            user_id = user.id

        async with session_factory() as session:
            fetched = await ConversationRepository(session).get_by_id(conversation_id)
            assert fetched is not None
            assert fetched.title == "unit test conversation"
            assert fetched.user_id == user_id

        await _delete_conversation(conversation_id)
        await _delete_user(user_id)

    asyncio.run(run())


async def _create_conversation_with_user(
    session, title: str
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a user + conversation in the given session (caller commits)."""
    user = User(id=uuid.uuid4())
    session.add(user)
    await session.flush()
    conversation = await ConversationRepository(session).create(user.id, title)
    return conversation.id, user.id


def test_message_creation() -> None:
    _require_db()

    async def run() -> None:
        async with session_factory() as session:
            conversation_id, user_id = await _create_conversation_with_user(
                session, "message creation test"
            )
            message = await MessageRepository(session).create(
                conversation_id, "user", "created but maybe not re-read yet"
            )
            await session.commit()
            assert message.id is not None
            assert message.role == "user"
            assert message.created_at is not None
            assert message.created_at.tzinfo is not None

        await _delete_conversation(conversation_id)
        await _delete_user(user_id)

    asyncio.run(run())


def test_message_persistence() -> None:
    _require_db()

    async def run() -> None:
        async with session_factory() as session:
            conversation_id, user_id = await _create_conversation_with_user(
                session, "persistence test"
            )
            await MessageRepository(session).create(
                conversation_id, "user", "first test message"
            )
            await MessageRepository(session).create(
                conversation_id, "assistant", "first test reply"
            )
            await session.commit()

        # New session — proves the rows really hit PostgreSQL.
        async with session_factory() as session:
            messages = await MessageRepository(session).list_for_conversation(
                conversation_id
            )
            assert len(messages) == 2
            assert messages[0].role == "user"
            assert messages[0].content == "first test message"
            assert messages[1].role == "assistant"
            assert messages[1].content == "first test reply"

        await _delete_conversation(conversation_id)
        await _delete_user(user_id)

    asyncio.run(run())


def test_conversation_retrieval_api() -> None:
    _require_db()

    created = client.post("/api/conversations", json={"title": "retrieval test"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    try:
        listed = client.get("/api/conversations")
        assert listed.status_code == 200
        assert any(c["id"] == conversation_id for c in listed.json())

        fetched = client.get(f"/api/conversations/{conversation_id}")
        assert fetched.status_code == 200
        assert fetched.json()["title"] == "retrieval test"

        messages = client.get(f"/api/conversations/{conversation_id}/messages")
        assert messages.status_code == 200
        assert messages.json() == []
    finally:
        asyncio.run(_delete_conversation(uuid.UUID(conversation_id)))


def test_invalid_conversation_id() -> None:
    _require_db()

    missing_id = str(uuid.uuid4())
    assert client.get(f"/api/conversations/{missing_id}").status_code == 404
    assert (
        client.get(f"/api/conversations/{missing_id}/messages").status_code == 404
    )
    chat = client.post(
        "/api/chat",
        json={"message": "hello", "conversation_id": missing_id},
    )
    assert chat.status_code == 404


def test_chat_persistence() -> None:
    _require_db()

    first = client.post("/api/chat", json={"message": "chat persistence turn one"})
    assert first.status_code == 200
    first_data = first.json()
    conversation_id = first_data["conversation_id"]
    assert first_data["message"] == "chat persistence turn one"
    assert first_data["response"]

    try:
        second = client.post(
            "/api/chat",
            json={
                "message": "chat persistence turn two",
                "conversation_id": conversation_id,
            },
        )
        assert second.status_code == 200
        assert second.json()["conversation_id"] == conversation_id

        messages = client.get(f"/api/conversations/{conversation_id}/messages")
        assert messages.status_code == 200
        rows = messages.json()
        assert len(rows) == 4
        assert sum(1 for m in rows if m["role"] == "user") == 2
        assert sum(1 for m in rows if m["role"] == "assistant") == 2
        contents = [m["content"] for m in rows]
        assert "chat persistence turn one" in contents
        assert "chat persistence turn two" in contents
    finally:
        asyncio.run(_delete_conversation(uuid.UUID(conversation_id)))


def test_message_retrieval_api() -> None:
    """Messages written via repositories are returned through the API."""

    async def seed() -> tuple[str, list[str]]:
        async with session_factory() as session:
            conversation_id, user_id = await _create_conversation_with_user(
                session, "message retrieval test"
            )
            m1 = await MessageRepository(session).create(
                conversation_id, "user", "retrieval: hello"
            )
            m2 = await MessageRepository(session).create(
                conversation_id, "assistant", "retrieval: hi back"
            )
            await session.commit()
            return str(conversation_id), [str(m1.id), str(m2.id), str(user_id)]

    _require_db()
    conversation_id, ids = asyncio.run(seed())

    try:
        rows = client.get(f"/api/conversations/{conversation_id}/messages").json()
        assert [m["content"] for m in rows] == ["retrieval: hello", "retrieval: hi back"]
        assert [m["role"] for m in rows] == ["user", "assistant"]
        assert {m["id"] for m in rows} == set(ids[:2])
    finally:
        asyncio.run(
            _delete_conversation(uuid.UUID(conversation_id))
        )  # messages cascade with conversation


def test_multiple_messages_same_conversation() -> None:
    _require_db()

    first = client.post("/api/chat", json={"message": "multi turn alpha"})
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]

    try:
        for i, text in enumerate(("multi turn beta", "multi turn gamma"), start=2):
            response = client.post(
                "/api/chat",
                json={"message": text, "conversation_id": conversation_id},
            )
            assert response.status_code == 200
            assert response.json()["conversation_id"] == conversation_id

        rows = client.get(f"/api/conversations/{conversation_id}/messages").json()
        assert len(rows) == 6
        assert sum(1 for m in rows if m["role"] == "user") == 3
        assert sum(1 for m in rows if m["role"] == "assistant") == 3
        user_contents = [m["content"] for m in rows if m["role"] == "user"]
        assert user_contents == ["multi turn alpha", "multi turn beta", "multi turn gamma"]
    finally:
        asyncio.run(_delete_conversation(uuid.UUID(conversation_id)))
