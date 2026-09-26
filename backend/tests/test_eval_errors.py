"""Phase 7 error-handling evaluation — controlled HTTP failures only."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_empty_message_422() -> None:
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_missing_message_422() -> None:
    assert client.post("/api/chat", json={}).status_code == 422


def test_whitespace_message_422() -> None:
    assert client.post("/api/chat", json={"message": "   \n\t "}).status_code == 422


def test_invalid_uuid_conversation_422() -> None:
    resp = client.post(
        "/api/chat",
        json={"message": "hello", "conversation_id": "not-a-uuid"},
    )
    assert resp.status_code == 422


def test_missing_conversation_404() -> None:
    resp = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "conversation_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_malformed_json_422() -> None:
    resp = client.post(
        "/api/chat",
        content="{not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_no_stack_trace_in_chat_errors() -> None:
    resp = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "conversation_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    body = resp.text.lower()
    assert "traceback" not in body
    assert "file \"" not in body


def test_invalid_screening_id_404() -> None:
    resp = client.get("/api/screening/phq9/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404


def test_invalid_phq9_answer_4xx() -> None:
    start = client.post("/api/screening/phq9/start")
    if start.status_code == 409:
        # finish leftover
        return
    sid = start.json()["screening_id"]
    resp = client.post(
        f"/api/screening/phq9/{sid}/answer",
        json={"question_number": 1, "answer": 99},
    )
    assert resp.status_code in (400, 409, 422)
    # cleanup
    for q in range(1, 10):
        client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": 0},
        )
    client.post(f"/api/screening/phq9/{sid}/complete")


def test_health_ok() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"ok", "healthy", "degraded"} or "version" in resp.json()
