"""Phase 7 PHQ-9 lifecycle evaluation (API-level, synthetic answers)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database.connection import session_factory
from app.main import app
from app.models import ScreeningSession
from app.services import phq9

client = TestClient(app)


def _clear_in_progress() -> None:
    """Delete any leftover in-progress rows (single default user, test isolation)."""
    if session_factory is None:
        return

    async def run() -> None:
        async with session_factory() as session:
            from sqlalchemy import select

            rows = (
                await session.execute(
                    select(ScreeningSession).where(
                        ScreeningSession.status == "in_progress",
                    )
                )
            ).scalars().all()
            for row in rows:
                await session.delete(row)
            await session.commit()

    asyncio.run(run())


@pytest.fixture(scope="module", autouse=True)
def _isolate_module():
    """Clear leftover in-progress sessions once; do not race mid-test."""
    _clear_in_progress()
    yield
    _clear_in_progress()


def _start_ok() -> dict:
    start = client.post("/api/screening/phq9/start")
    if start.status_code == 409:
        _clear_in_progress()
        start = client.post("/api/screening/phq9/start")
    assert start.status_code == 201, start.text
    return start.json()


def test_phq9_score_bands() -> None:
    assert phq9.severity_band(0) == ("minimal", "Minimal")
    assert phq9.severity_band(4) == ("minimal", "Minimal")
    assert phq9.severity_band(5) == ("mild", "Mild")
    assert phq9.severity_band(9) == ("mild", "Mild")
    assert phq9.severity_band(10) == ("moderate", "Moderate")
    assert phq9.severity_band(14) == ("moderate", "Moderate")
    assert phq9.severity_band(15) == ("moderately_severe", "Moderately severe")
    assert phq9.severity_band(19) == ("moderately_severe", "Moderately severe")
    assert phq9.severity_band(20) == ("severe", "Severe")
    assert phq9.severity_band(27) == ("severe", "Severe")


def test_phq9_score_all_zeros_and_all_max() -> None:
    assert phq9.score_phq9([0] * 9) == 0
    assert phq9.score_phq9([3] * 9) == 27


def test_phq9_disclaimer_not_diagnosis() -> None:
    assert "diagnose" in phq9.DISCLAIMER.lower() or "diagnosis" in phq9.DISCLAIMER.lower()
    assert "does not" in phq9.DISCLAIMER.lower()


def test_phq9_full_lifecycle_api() -> None:
    data = _start_ok()
    sid = data["screening_id"]
    assert data["question_number"] == 1
    assert data["total_questions"] == 9

    for q in range(1, 10):
        ans = 2
        resp = client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": ans},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if q < 9:
            assert body["question_number"] == q + 1
        else:
            assert body.get("complete_ready") is True

    # Out-of-order / invalid
    bad = client.post(
        f"/api/screening/phq9/{sid}/answer",
        json={"question_number": 1, "answer": 1},
    )
    assert bad.status_code in (400, 409, 422)

    complete = client.post(f"/api/screening/phq9/{sid}/complete")
    assert complete.status_code == 200, complete.text
    result = complete.json()
    assert result["score"] == 18  # 9 × 2
    assert result["severity"] == "moderately_severe"
    assert result["disclaimer"]
    # Item 9 = 2 → positive → safety probe
    assert result["safety"] is not None
    assert result["safety"]["item9_positive"] is True
    # ITEM9_SAFETY_PROBE contains self-harm → requires_safety_response True
    assert result["safety"]["requires_safety_response"] is True
    assert result["safety"]["safety_response"]


def test_phq9_incomplete_complete_rejected() -> None:
    data = _start_ok()
    sid = data["screening_id"]
    client.post(
        f"/api/screening/phq9/{sid}/answer",
        json={"question_number": 1, "answer": 0},
    )
    complete = client.post(f"/api/screening/phq9/{sid}/complete")
    assert complete.status_code in (400, 409)
    # finish for isolation (fixture also clears)
    for q in range(2, 10):
        client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": 0},
        )
    client.post(f"/api/screening/phq9/{sid}/complete")


def test_phq9_invalid_answer_rejected() -> None:
    data = _start_ok()
    sid = data["screening_id"]
    bad = client.post(
        f"/api/screening/phq9/{sid}/answer",
        json={"question_number": 1, "answer": 5},
    )
    assert bad.status_code in (400, 409, 422)
    for q in range(1, 10):
        client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": 0},
        )
    client.post(f"/api/screening/phq9/{sid}/complete")


def test_phq9_item9_zero_no_safety() -> None:
    data = _start_ok()
    sid = data["screening_id"]
    for q in range(1, 10):
        client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": 1 if q != 9 else 0},
        )
    result = client.post(f"/api/screening/phq9/{sid}/complete").json()
    assert result["score"] == 8
    assert result["severity"] == "mild"
    assert result["safety"] is None or result["safety"]["item9_positive"] is False


def test_phq9_completed_session_cannot_answer() -> None:
    data = _start_ok()
    sid = data["screening_id"]
    for q in range(1, 10):
        client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": 0},
        )
    client.post(f"/api/screening/phq9/{sid}/complete")
    again = client.post(
        f"/api/screening/phq9/{sid}/answer",
        json={"question_number": 1, "answer": 1},
    )
    assert again.status_code in (400, 409)
    double = client.post(f"/api/screening/phq9/{sid}/complete")
    assert double.status_code in (400, 409)


def test_phq9_state_resume_shape() -> None:
    data = _start_ok()
    sid = data["screening_id"]
    client.post(
        f"/api/screening/phq9/{sid}/answer",
        json={"question_number": 1, "answer": 2},
    )
    state = client.get(f"/api/screening/phq9/{sid}")
    assert state.status_code == 200
    body = state.json()
    assert body["answered_count"] == 1
    assert body["question_number"] == 2
    assert body["status"] == "in_progress"
    for q in range(2, 10):
        client.post(
            f"/api/screening/phq9/{sid}/answer",
            json={"question_number": q, "answer": 0},
        )
    client.post(f"/api/screening/phq9/{sid}/complete")
