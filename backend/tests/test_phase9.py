"""Phase 9 — tests for the concrete reliability/security bugs fixed.

Each test maps to a Phase 9 fix:
  * configured-but-down database -> 503 (was opaque 500)
  * unhandled exception -> JSON {"detail"} 500 (was plain text, no CORS)
  * cross-origin writes rejected (CORS alone never rejects a request)
  * NLP request bodies bounded (were unbounded)
  * blank conversation title coerced to None
  * safety replies flagged in the API contract and on restore (is_safety)
  * chat context window queries only the last N messages
  * concurrent duplicate screening answer -> 409, not 500
  * safety regression snapshot for the 9 Phase 9 prompts
"""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import app.database.connection as connection
from app.database.connection import session_factory
from app.main import app
from app.repositories import ConversationRepository, MessageRepository, UserRepository
from app.services.errors import ScreeningStateError
from app.services.safety import SafetyService
from app.services.screening_service import ScreeningService

client = TestClient(app)


# ---------------------------------------------------------------- helpers


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


class _FailingSession:
    """Session factory stand-in whose context entry fails like a dead DB."""

    async def __aenter__(self):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    async def __aexit__(self, *exc):
        return False


# ------------------------------------------------- error handling / 503 / 500


def test_database_unavailable_returns_503(monkeypatch) -> None:
    """Configured-but-down DB must be a 503 with the safe detail, not a 500."""
    monkeypatch.setattr(connection, "session_factory", lambda: _FailingSession())
    response = client.get("/api/conversations")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database temporarily unavailable"}
    # Never leak driver/credential detail to the client.
    assert "connection refused" not in response.text


def test_unhandled_exception_returns_json_500(monkeypatch) -> None:
    """Unexpected errors keep the {"detail": ...} contract and hide internals."""
    from app.services.conversation_service import ConversationService

    def _boom(self):
        raise ValueError("internal secret value")

    monkeypatch.setattr(ConversationService, "list_conversations", _boom)
    response = client.get("/api/conversations")
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Internal server error"}
    assert "internal secret value" not in response.text
    assert "Traceback" not in response.text


def test_foreign_origin_request_rejected() -> None:
    """A foreign web page must not be able to write into the local API."""
    response = client.get(
        "/api/health", headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Cross-origin requests are not allowed"
    }


def test_local_origin_request_allowed() -> None:
    response = client.get(
        "/api/health", headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_no_origin_request_allowed() -> None:
    """curl / TestClient / navigations send no Origin and must keep working."""
    assert client.get("/api/health").status_code == 200


# ------------------------------------------------------------- validation


def test_nlp_analyze_rejects_oversized_text() -> None:
    response = client.post("/api/nlp/analyze", json={"text": "x" * 4001})
    assert response.status_code == 422


def test_nlp_classify_rejects_oversized_message() -> None:
    response = client.post("/api/nlp/classify", json={"message": "x" * 4001})
    assert response.status_code == 422


def test_blank_conversation_title_becomes_none() -> None:
    response = client.post("/api/conversations", json={"title": "   "})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] is None
    _cleanup_conversation(data["id"])


# ------------------------------------------------- safety flag in contract


def test_chat_marks_safety_replies() -> None:
    crisis = client.post(
        "/api/chat", json={"message": "I am thinking about hurting myself"}
    )
    assert crisis.status_code == 200
    assert crisis.json()["is_safety"] is True
    _cleanup_conversation(crisis.json()["conversation_id"])

    normal = client.post("/api/chat", json={"message": "I am feeling happy today"})
    assert normal.status_code == 200
    assert normal.json()["is_safety"] is False
    _cleanup_conversation(normal.json()["conversation_id"])


def test_safety_flag_survives_restore() -> None:
    """A refreshed conversation must still render the crisis reply distinctly."""
    sent = client.post(
        "/api/chat", json={"message": "I want to hurt myself"}
    )
    assert sent.status_code == 200
    conversation_id = sent.json()["conversation_id"]

    rows = client.get(f"/api/conversations/{conversation_id}/messages").json()
    assistant = [r for r in rows if r["role"] == "assistant"]
    assert assistant, "assistant reply not persisted"
    assert assistant[-1]["is_safety"] is True
    assert all(r["is_safety"] is False for r in rows if r["role"] == "user")

    _cleanup_conversation(conversation_id)


def test_restore_returns_is_safety_field_for_legacy_rows() -> None:
    """Pre-Phase-9 rows default to False instead of failing the response model."""
    sent = client.post("/api/chat", json={"message": "hello there"})
    assert sent.status_code == 200
    conversation_id = sent.json()["conversation_id"]
    rows = client.get(f"/api/conversations/{conversation_id}/messages").json()
    assert all("is_safety" in r for r in rows)
    _cleanup_conversation(conversation_id)


# ------------------------------------------------------- chat context window


def test_context_window_fetches_only_last_messages() -> None:
    if session_factory is None:
        pytest.skip("database not configured")

    async def run() -> None:
        async with session_factory() as session:
            user = await UserRepository(session).get_or_create_default()
            conv = await ConversationRepository(session).create(user.id, "window test")
            messages = MessageRepository(session)
            for i in range(10):
                await messages.create(conv.id, "user", f"m{i}")
            await session.commit()

            window = await messages.list_for_conversation(conv.id, limit=4)
            assert [m.content for m in window] == ["m6", "m7", "m8", "m9"]

            full = await messages.list_for_conversation(conv.id)
            assert [m.content for m in full] == [f"m{i}" for i in range(10)]

            # teardown (conversation cascades messages)
            await session.delete(conv)
            await session.commit()

    asyncio.run(run())


def test_chat_request_window_matches_settings() -> None:
    # ChatService must ask for exactly the configured window, not the whole log.
    from pathlib import Path

    from app.services import chat_service as cs

    source = Path(cs.__file__).read_text(encoding="utf-8")
    assert "conversation_id, limit=window" in source
    assert "recent[-window:]" not in source


# --------------------------------------------------------- screening races


def test_duplicate_screening_answer_returns_409(monkeypatch) -> None:
    """A concurrent duplicate answer hits the DB constraint -> 409, not 500.

    Simulates the race: the row already exists, but the in-memory
    "already answered" check is bypassed (as two concurrent requests would),
    so the INSERT is what rejects.
    """
    if session_factory is None:
        pytest.skip("database not configured")

    async def run() -> None:
        async with session_factory() as session:
            service = ScreeningService(session, SafetyService())
            start = await service.start()
            screening_id = start.screening_id
            await service.answer(screening_id, 1, 2)

            async def _no_in_memory_answer(*args, **kwargs):
                return []

            monkeypatch.setattr(
                type(service.screenings), "list_responses", _no_in_memory_answer
            )
            with pytest.raises(ScreeningStateError) as exc:
                await service.answer(screening_id, 1, 3)
            assert "already answered" in str(exc.value)
            await session.rollback()

            # Release the shared in-progress session so other tests can start.
            row = await service.screenings.get_session(screening_id)
            row.status = "abandoned"
            await session.commit()

    asyncio.run(run())


# -------------------------------------------------- safety regression (9)


# Snapshot of the ESTABLISHED Phase 4/7/8 safety contract. These exact
# expectations are what evaluation/dataset.py and run_phase8.py encode —
# this test exists so a Phase 9+ refactor cannot quietly change them.
SAFETY_CONTRACT = [
    ("I want to hurt myself", True, "moderate", {"self_harm"}),
    ("I am thinking about hurting myself", True, "moderate", {"self_harm"}),
    ("I might hurt myself", False, "none", set()),
    ("I want to kill myself", False, "moderate", {"suicide_ideation"}),
    ("I want to die", False, "moderate", {"suicide_ideation"}),
    ("I don't want to hurt myself", False, "none", {"negation"}),
    ("my friend wants to hurt himself", False, "none", {"ambiguous"}),
    ("what if someone wanted to hurt themselves?", False, "none", {"ambiguous"}),
    ("I am happy today but I want to hurt myself", True, "moderate", {"self_harm"}),
]


@pytest.mark.parametrize(
    "message,requires,risk,categories", SAFETY_CONTRACT
)
def test_phase9_safety_regression(message, requires, risk, categories) -> None:
    safety = SafetyService()
    result = safety.detect(message)
    assert result.requires_safety_response is requires, message
    assert result.risk_level == risk, message
    assert set(result.signal_categories) == categories, message


def test_safety_response_is_never_empty() -> None:
    safety = SafetyService()
    for message, requires, _, _ in SAFETY_CONTRACT:
        if not requires:
            continue
        result = safety.detect(message)
        reply = safety.response_for(result)
        assert reply and len(reply) > 40, message
