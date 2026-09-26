import asyncio
import uuid

from fastapi.testclient import TestClient

from app.database.connection import session_factory
from app.main import app
from app.models import Conversation

client = TestClient(app)


def _cleanup_conversation(conversation_id: str) -> None:
    """Remove a conversation created by a test so runs stay repeatable."""
    if session_factory is None or not conversation_id:
        return

    async def run() -> None:
        async with session_factory() as session:
            conversation = await session.get(Conversation, uuid.UUID(conversation_id))
            if conversation is not None:
                await session.delete(conversation)
                await session.commit()

    asyncio.run(run())


def test_root_returns_project_info() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TOM"
    assert data["status"] == "running"
    assert "version" in data


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "TOM"


def test_chat_endpoint_echoes_message() -> None:
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "hello"
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0
    assert data["conversation_id"]
    _cleanup_conversation(data["conversation_id"])


def test_chat_endpoint_handles_normal_message() -> None:
    response = client.post("/api/chat", json={"message": "I feel stressed about exams"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "I feel stressed about exams"
    assert data["response"]
    _cleanup_conversation(data["conversation_id"])


def test_chat_rejects_empty_message() -> None:
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_rejects_whitespace_only_message() -> None:
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 422


def test_chat_rejects_missing_message() -> None:
    response = client.post("/api/chat", json={})
    assert response.status_code == 422


def test_cors_preflight_allows_local_frontend() -> None:
    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == (
        "http://localhost:5173"
    )


def test_cors_rejects_unknown_origin() -> None:
    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_database_not_configured_returns_503(monkeypatch) -> None:
    import app.database.connection as connection

    monkeypatch.setattr(connection, "session_factory", None)
    response = client.get("/api/conversations")
    assert response.status_code == 503
    assert "Database" in response.json()["detail"]
