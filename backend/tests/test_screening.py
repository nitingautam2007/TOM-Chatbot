"""Phase 5 — PHQ-9 structured depressive-symptom screening tests.

Screening is NOT a diagnosis. Item 9 routes through Phase 4 SafetyService.
Inputs are synthetic. DB tests follow the Phase 2 pattern (skip if unconfigured).
"""

from __future__ import annotations

import asyncio
import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import settings
from app.database.connection import db_not_configured_message, session_factory
from app.main import app
from app.models import ScreeningResponse, ScreeningSession, User
from app.schemas.screening import ScreeningAnswerRequest
from app.services import phq9
from app.services.errors import ScreeningStateError
from app.services.screening_service import ScreeningService

client = TestClient(app)


def _require_db() -> None:
    if session_factory is None:
        pytest.skip(db_not_configured_message())


async def _cleanup_screening(screening_id: uuid.UUID) -> None:
    if session_factory is None:
        return
    async with session_factory() as session:
        row = await session.get(ScreeningSession, screening_id)
        if row is not None:
            await session.delete(row)
            await session.commit()


async def _cleanup_user(user_id: uuid.UUID) -> None:
    if session_factory is None:
        return
    async with session_factory() as session:
        user = await session.get(User, user_id)
        if user is not None:
            await session.delete(user)
            await session.commit()


def _cleanup(screening_id: str | None) -> None:
    if not screening_id:
        return

    async def run() -> None:
        await _cleanup_screening(uuid.UUID(screening_id))

    if session_factory is not None:
        asyncio.run(run())


def _start() -> dict:
    resp = client.post("/api/screening/phq9/start")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _answer(screening_id: str, question_number: int, answer) -> dict:
    return client.post(
        f"/api/screening/phq9/{screening_id}/answer",
        json={"question_number": question_number, "answer": answer},
    )


def _answer_all(screening_id: str, answers: list[int] | None = None) -> None:
    answers = answers if answers is not None else [1] * 9
    for i, a in enumerate(answers, start=1):
        resp = _answer(screening_id, i, a)
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Pure scoring (no DB)
# ---------------------------------------------------------------------------
def test_score_calculation() -> None:
    assert phq9.score_phq9([1] * 9) == 9
    assert phq9.score_phq9({i: 2 for i in range(1, 10)}) == 18


def test_score_min_0() -> None:
    assert phq9.score_phq9([0] * 9) == 0
    assert phq9.severity_band(0) == ("minimal", "Minimal")


def test_score_max_27() -> None:
    assert phq9.score_phq9([3] * 9) == 27
    assert phq9.severity_band(27) == ("severe", "Severe")


@pytest.mark.parametrize(
    ("score", "key"),
    [
        (0, "minimal"),
        (4, "minimal"),
        (5, "mild"),
        (9, "mild"),
        (10, "moderate"),
        (14, "moderate"),
        (15, "moderately_severe"),
        (19, "moderately_severe"),
        (20, "severe"),
        (27, "severe"),
    ],
)
def test_severity_boundaries(score: int, key: str) -> None:
    assert phq9.severity_band(score)[0] == key


def test_nine_questions_and_timeframe() -> None:
    assert phq9.PHQ9_TOTAL_QUESTIONS == 9
    assert len(phq9.QUESTIONS) == 9
    assert phq9.PHQ9_TIMEFRAME == "Over the last 2 weeks"
    assert len(phq9.ANSWER_CHOICES) == 4


def test_item9_value() -> None:
    assert phq9.item9_value([0] * 9) == 0
    assert phq9.item9_value({i: 1 for i in range(1, 9)} | {9: 3}) == 3


def test_disclaimer_is_nondiagnostic() -> None:
    assert "does not by itself diagnose" in phq9.DISCLAIMER.lower()


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def test_schema_rejects_negative_answer() -> None:
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=1, answer=-1)


def test_schema_rejects_answer_gt_3() -> None:
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=1, answer=4)


def test_schema_rejects_decimal_answer() -> None:
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=1, answer=1.5)  # type: ignore[arg-type]


def test_schema_rejects_string_answer() -> None:
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=1, answer="2")  # type: ignore[arg-type]


def test_schema_rejects_missing_answer() -> None:
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=1)  # type: ignore[call-arg]


def test_schema_rejects_invalid_question_number() -> None:
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=0, answer=0)
    with pytest.raises(ValidationError):
        ScreeningAnswerRequest(question_number=10, answer=0)


def test_schema_accepts_valid_pairs() -> None:
    for q in range(1, 10):
        for a in range(0, 4):
            req = ScreeningAnswerRequest(question_number=q, answer=a)
            assert req.answer == a


# ---------------------------------------------------------------------------
# API: lifecycle (DB)
# ---------------------------------------------------------------------------
def test_start_screening() -> None:
    _require_db()
    data = _start()
    try:
        assert data["screening_type"] == "phq9"
        assert data["status"] == "in_progress"
        assert data["question_number"] == 1
        assert data["total_questions"] == 9
        assert data["timeframe"] == "Over the last 2 weeks"
        assert len(data["choices"]) == 4
    finally:
        _cleanup(data["screening_id"])


def test_start_screening_twice_conflicts() -> None:
    _require_db()
    data = _start()
    try:
        resp = client.post("/api/screening/phq9/start")
        assert resp.status_code == 409
    finally:
        _cleanup(data["screening_id"])


def test_valid_answers_0_to_3() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        for a in range(0, 4):
            resp = _answer(sid, a + 1, a)
            assert resp.status_code == 200, resp.text
            assert resp.json()["answered_count"] == a + 1
        # finish remaining with 0s so cleanup path is clear
        for q in range(5, 10):
            assert _answer(sid, q, 0).status_code == 200
    finally:
        _cleanup(sid)


def test_invalid_negative_answer_api() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 1, -1).status_code == 422
    finally:
        _cleanup(data["screening_id"])


def test_invalid_answer_gt_3_api() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 1, 4).status_code == 422
    finally:
        _cleanup(data["screening_id"])


def test_decimal_answer_api() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 1, 1.5).status_code == 422
    finally:
        _cleanup(data["screening_id"])


def test_string_answer_api() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 1, "2").status_code == 422
    finally:
        _cleanup(data["screening_id"])


def test_missing_answer_api() -> None:
    _require_db()
    data = _start()
    try:
        resp = client.post(
            f"/api/screening/phq9/{data['screening_id']}/answer",
            json={"question_number": 1},
        )
        assert resp.status_code == 422
    finally:
        _cleanup(data["screening_id"])


def test_invalid_question_number_api() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 10, 0).status_code == 422
        assert _answer(data["screening_id"], 0, 0).status_code == 422
    finally:
        _cleanup(data["screening_id"])


def test_duplicate_answer_rejected() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 1, 1).status_code == 200
        assert _answer(data["screening_id"], 1, 2).status_code == 409
    finally:
        _cleanup(data["screening_id"])


def test_out_of_order_answer_rejected() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 2, 1).status_code == 409
    finally:
        _cleanup(data["screening_id"])


def test_incomplete_completion_rejected() -> None:
    _require_db()
    data = _start()
    try:
        assert _answer(data["screening_id"], 1, 1).status_code == 200
        resp = client.post(f"/api/screening/phq9/{data['screening_id']}/complete")
        assert resp.status_code == 409
    finally:
        _cleanup(data["screening_id"])


def test_complete_9_question_screening() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        _answer_all(sid, [0] * 9)
        resp = client.post(f"/api/screening/phq9/{sid}/complete")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert body["score"] == 0
        assert body["severity"] == "minimal"
        assert body["severity_label"] == "Minimal"
        assert "diagnose" in body["disclaimer"].lower()
        assert body["safety"] is None  # item9 == 0
        assert body["completed_at"]
    finally:
        _cleanup(sid)


def test_completed_screening_cannot_be_modified() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        _answer_all(sid, [1] * 9)
        assert client.post(f"/api/screening/phq9/{sid}/complete").status_code == 200
        assert _answer(sid, 1, 2).status_code == 409
        assert client.post(f"/api/screening/phq9/{sid}/complete").status_code == 409
    finally:
        _cleanup(sid)


def test_get_screening_state() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        resp = client.get(f"/api/screening/phq9/{sid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "in_progress"
        assert body["answered_count"] == 0
        assert body["question_number"] == 1

        _answer(sid, 1, 2)
        body = client.get(f"/api/screening/phq9/{sid}").json()
        assert body["answered_count"] == 1
        assert body["question_number"] == 2
    finally:
        _cleanup(sid)


def test_get_unknown_screening_404() -> None:
    _require_db()
    resp = client.get(f"/api/screening/phq9/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_item9_zero_no_safety() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        _answer_all(sid, [2] * 8 + [0])
        body = client.post(f"/api/screening/phq9/{sid}/complete").json()
        assert body["score"] == 16
        assert body["severity"] == "moderately_severe"
        assert body["safety"] is None
    finally:
        _cleanup(sid)


def test_item9_positive_triggers_safety() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        _answer_all(sid, [1] * 8 + [1])
        body = client.post(f"/api/screening/phq9/{sid}/complete").json()
        assert body["score"] == 9
        assert body["severity"] == "mild"
        assert body["safety"] is not None
        assert body["safety"]["item9_positive"] is True
        # Phase 4 is authoritative — item9=1 does NOT imply high/imminent.
        assert body["safety"]["risk_level"] in {
            "none",
            "low",
            "moderate",
            "high",
            "imminent",
            "unknown",
        }
    finally:
        _cleanup(sid)


def test_score_and_persistence_roundtrip() -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        # score 12 → moderate: eight 1s + one 4? max 3 → 4*3=12 needs mix
        answers = [2, 2, 2, 2, 1, 1, 1, 1, 0]  # = 12
        _answer_all(sid, answers)
        body = client.post(f"/api/screening/phq9/{sid}/complete").json()
        assert body["score"] == 12
        assert body["severity"] == "moderate"
        assert body["severity_label"] == "Moderate"

        # persistence via GET
        state = client.get(f"/api/screening/phq9/{sid}").json()
        assert state["status"] == "completed"
        assert state["score"] == 12
        assert state["severity"] == "moderate"
        assert state["disclaimer"]

        # persistence via repository
        async def run() -> None:
            async with session_factory() as session:
                row = await session.get(ScreeningSession, uuid.UUID(sid))
                assert row is not None
                assert row.score == 12
                assert row.severity == "moderate"
                assert row.status == "completed"
                assert row.completed_at is not None

        asyncio.run(run())
    finally:
        _cleanup(sid)


def test_user_cannot_access_another_users_screening() -> None:
    _require_db()

    async def create_other() -> tuple[uuid.UUID, uuid.UUID]:
        from app.repositories import ScreeningRepository

        async with session_factory() as session:
            other = User(id=uuid.uuid4())
            session.add(other)
            await session.flush()
            row = await ScreeningRepository(session).create_session(other.id, "phq9")
            await session.commit()
            return row.id, other.id

    screening_id, other_user_id = asyncio.run(create_other())
    try:
        resp = client.get(f"/api/screening/phq9/{screening_id}")
        # Default-user session does not own this screening → 404 (no leak).
        assert resp.status_code == 404
        resp = client.post(f"/api/screening/phq9/{screening_id}/complete")
        assert resp.status_code == 404
        resp = client.post(
            f"/api/screening/phq9/{screening_id}/answer",
            json={"question_number": 1, "answer": 1},
        )
        assert resp.status_code == 404
    finally:
        asyncio.run(_cleanup_screening(screening_id))
        asyncio.run(_cleanup_user(other_user_id))


def test_no_sensitive_screening_data_in_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _require_db()
    data = _start()
    sid = data["screening_id"]
    try:
        with caplog.at_level(logging.DEBUG):
            _answer_all(sid, [3, 2, 1, 0, 3, 2, 1, 0, 3])
            client.post(f"/api/screening/phq9/{sid}/complete")

        # Questionnaire answers must never appear in log records.
        for record in caplog.records:
            msg = record.getMessage()
            assert "response_value" not in msg
            # answer payload patterns like "answer": 3
            assert '"answer"' not in msg
    finally:
        _cleanup(sid)


def test_chat_unaffected_by_phase5() -> None:
    """Regression: normal chat path unchanged (no auto screening)."""
    resp = client.post("/api/chat", json={"message": "I feel a bit sad today"})
    assert resp.status_code == 200
    body = resp.json()
    assert "phq9" not in body["response"].lower()
    assert "screening" not in body["response"].lower()
    _cleanup(body.get("conversation_id"))


def test_health_version() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == "0.10.0-phase10"
    assert settings.version == "0.10.0-phase10"


# ---------------------------------------------------------------------------
# Unit: SafetyService interaction (spy, no DB answers beyond service)
# ---------------------------------------------------------------------------
class _SpySafety:
    def __init__(self, risk="moderate", requires=False):
        self.risk = risk
        self.requires = requires
        self.detect_calls: list[str] = []

    def detect(self, text, language=None):
        from app.services.safety.types import SafetyResult

        self.detect_calls.append(text)
        return SafetyResult(
            risk_level=self.risk,  # type: ignore[arg-type]
            requires_safety_response=self.requires,
            language="en",
            processing_time_ms=0.1,
        )

    def response_for(self, result):
        return "SPY_CRISIS_RESPONSE"


def _service_with(safety) -> ScreeningService:
    assert session_factory is not None
    session = session_factory()
    return ScreeningService(session, safety)


def _run(coro):
    return asyncio.run(coro)


def test_item9_invokes_safety_service() -> None:
    _require_db()
    spy = _SpySafety(risk="moderate", requires=False)

    async def run() -> None:
        async with session_factory() as session:
            svc = ScreeningService(session, spy)
            start = await svc.start()
            sid = start.screening_id
            try:
                for q in range(1, 9):
                    await svc.answer(sid, q, 1)
                await svc.answer(sid, 9, 1)
                result = await svc.complete(sid)
                assert result.safety is not None
                assert result.safety.item9_positive is True
                assert result.safety.risk_level == "moderate"
                assert result.safety.requires_safety_response is False
                assert len(spy.detect_calls) == 1
                # frequency NOT encoded in probe (item9=1 only)
                assert spy.detect_calls[0] == phq9.ITEM9_SAFETY_PROBE
            finally:
                await _cleanup_screening(sid)

    _run(run())


def test_item9_zero_does_not_invoke_safety() -> None:
    _require_db()
    spy = _SpySafety()

    async def run() -> None:
        async with session_factory() as session:
            svc = ScreeningService(session, spy)
            start = await svc.start()
            sid = start.screening_id
            try:
                for q in range(1, 10):
                    await svc.answer(sid, q, 0)
                result = await svc.complete(sid)
                assert result.safety is None
                assert spy.detect_calls == []
            finally:
                await _cleanup_screening(sid)

    _run(run())


def test_high_safety_overrides_ordinary_presentation() -> None:
    _require_db()
    spy = _SpySafety(risk="imminent", requires=True)

    async def run() -> None:
        async with session_factory() as session:
            svc = ScreeningService(session, spy)
            start = await svc.start()
            sid = start.screening_id
            try:
                for q in range(1, 9):
                    await svc.answer(sid, q, 2)
                await svc.answer(sid, 9, 3)
                result = await svc.complete(sid)
                assert result.safety is not None
                assert result.safety.requires_safety_response is True
                assert result.safety.safety_response == "SPY_CRISIS_RESPONSE"
                # Safety payload present for clients to prioritize over severity.
                assert result.safety.risk_level == "imminent"
                assert result.score == 19  # safety does not change the score
            finally:
                await _cleanup_screening(sid)

    _run(run())
