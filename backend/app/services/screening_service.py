"""ScreeningService — Phase 5 structured PHQ-9 screening workflow.

Owns the session lifecycle (start → answer ×9 → complete), scoring, and
item-9 → SafetyService routing. Scoring is pure arithmetic (no ML, no
embeddings). Questionnaire answers are never logged.

Ownership follows the existing single default-user mechanism (no auth yet).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.mixins import utcnow
from app.models import ScreeningSession
from app.models.screening import STATUS_COMPLETED, STATUS_IN_PROGRESS
from app.repositories import ScreeningRepository, UserRepository
from app.schemas.screening import (
    ScreeningChoice,
    ScreeningCompleteResponse,
    ScreeningSafetyStatus,
    ScreeningStartResponse,
    ScreeningStateResponse,
)
from app.services import phq9
from app.services.errors import ScreeningNotFoundError, ScreeningStateError
from app.services.safety import SafetyService, get_safety_service_singleton

logger = logging.getLogger(__name__)

_CHOICES = [
    ScreeningChoice(value=v, label=label) for v, label in phq9.ANSWER_CHOICES
]


class ScreeningService:
    """PHQ-9 screening session workflow (explicit — never auto-triggered from chat)."""

    def __init__(self, session: AsyncSession, safety: SafetyService | None = None):
        self.session = session
        self.users = UserRepository(session)
        self.screenings = ScreeningRepository(session)
        self.safety = safety or get_safety_service_singleton()

    async def _current_user_id(self) -> UUID:
        user = await self.users.get_or_create_default()
        return user.id

    async def _load_owned(self, screening_id: UUID) -> ScreeningSession:
        """Load a screening; 404 for missing or non-owned (no existence leak)."""
        row = await self.screenings.get_session(screening_id)
        user_id = await self._current_user_id()
        if row is None or row.user_id != user_id:
            raise ScreeningNotFoundError(screening_id)
        return row

    async def start(self) -> ScreeningStartResponse:
        user_id = await self._current_user_id()
        existing = await self.screenings.get_in_progress(user_id, phq9.PHQ9_TYPE)
        if existing is not None:
            raise ScreeningStateError("A PHQ-9 screening is already in progress")

        row = await self.screenings.create_session(user_id, phq9.PHQ9_TYPE)
        await self.session.commit()

        return ScreeningStartResponse(
            screening_id=row.id,
            screening_type=row.screening_type,
            status=row.status,
            question_number=1,
            total_questions=phq9.PHQ9_TOTAL_QUESTIONS,
            timeframe=phq9.PHQ9_TIMEFRAME,
            question=phq9.QUESTIONS[0],
            choices=list(_CHOICES),
        )

    async def answer(
        self, screening_id: UUID, question_number: int, answer: int
    ) -> ScreeningStateResponse:
        row = await self._load_owned(screening_id)

        if row.status != STATUS_IN_PROGRESS:
            raise ScreeningStateError("Screening is already completed")

        responses = await self.screenings.list_responses(row.id)
        answered = {r.question_number for r in responses}

        if question_number in answered:
            raise ScreeningStateError(
                f"Question {question_number} already answered"
            )

        expected = len(responses) + 1
        if question_number != expected:
            raise ScreeningStateError(
                f"Out of order: expected question {expected}"
            )

        if answer < phq9.ANSWER_MIN or answer > phq9.ANSWER_MAX:
            raise ScreeningStateError("Answer must be 0, 1, 2, or 3")

        try:
            await self.screenings.add_response(row.id, question_number, answer)
            await self.session.commit()
        except IntegrityError:
            # Two concurrent submissions passed the in-memory check; the DB
            # unique constraint is the real guard. Report 409, not 500.
            await self.session.rollback()
            raise ScreeningStateError(
                f"Question {question_number} already answered"
            ) from None

        return await self.state(screening_id)

    async def state(self, screening_id: UUID) -> ScreeningStateResponse:
        row = await self._load_owned(screening_id)
        responses = await self.screenings.list_responses(row.id)
        answered_count = len(responses)
        total = phq9.PHQ9_TOTAL_QUESTIONS

        base = dict(
            screening_id=row.id,
            screening_type=row.screening_type,
            status=row.status,
            total_questions=total,
            timeframe=phq9.PHQ9_TIMEFRAME,
            answered_count=answered_count,
        )

        if row.status == STATUS_COMPLETED:
            responses_map = {r.question_number: r.response_value for r in responses}
            safety = None
            if responses_map.get(9, 0) > 0:
                safety = self._item9_safety(responses_map)
            return ScreeningStateResponse(
                **base,
                score=row.score,
                severity=row.severity,
                severity_label=_label_for(row.severity),
                safety=safety,
                disclaimer=phq9.DISCLAIMER,
                completed_at=row.completed_at,
            )

        # In progress — next unanswered question (strictly sequential).
        next_q = answered_count + 1
        ready = answered_count == total
        if ready:
            return ScreeningStateResponse(**base, complete_ready=True)
        return ScreeningStateResponse(
            **base,
            question_number=next_q,
            question=phq9.QUESTIONS[next_q - 1],
            choices=list(_CHOICES),
        )

    async def complete(self, screening_id: UUID) -> ScreeningCompleteResponse:
        row = await self._load_owned(screening_id)

        if row.status != STATUS_IN_PROGRESS:
            raise ScreeningStateError("Screening is already completed")

        responses = await self.screenings.list_responses(row.id)
        if len(responses) != phq9.PHQ9_TOTAL_QUESTIONS:
            raise ScreeningStateError(
                f"Screening incomplete: {len(responses)}/"
                f"{phq9.PHQ9_TOTAL_QUESTIONS} questions answered"
            )

        responses_map = {r.question_number: r.response_value for r in responses}
        total_score = phq9.score_phq9(responses_map)
        severity_key, severity_label = phq9.severity_band(total_score)

        item9 = phq9.item9_value(responses_map)
        safety_status = None
        if item9 > 0:
            safety_status = self._item9_safety(responses_map)

        row.score = total_score
        row.severity = severity_key
        row.status = STATUS_COMPLETED
        row.completed_at = utcnow()
        await self.session.commit()

        return ScreeningCompleteResponse(
            screening_id=row.id,
            status=row.status,
            score=total_score,
            severity=severity_key,
            severity_label=severity_label,
            disclaimer=phq9.DISCLAIMER,
            safety=safety_status,
            completed_at=row.completed_at,
        )

    def _item9_safety(self, responses: dict[int, int]) -> ScreeningSafetyStatus:
        """Route a positive item 9 through Phase 4 SafetyService (authoritative)."""
        item9 = responses.get(9, 0)
        if item9 <= 0:
            return ScreeningSafetyStatus(
                item9_positive=False,
                risk_level="none",
                requires_safety_response=False,
            )
        try:
            result = self.safety.detect(phq9.ITEM9_SAFETY_PROBE)
        except Exception:  # noqa: BLE001 — safety must not block screening completion
            logger.exception("Safety detection failed during PHQ-9 item-9 routing")
            return ScreeningSafetyStatus(
                item9_positive=True,
                risk_level="unknown",
                requires_safety_response=False,
            )

        crisis_text = None
        if result.requires_safety_response:
            crisis_text = self.safety.response_for(result)

        return ScreeningSafetyStatus(
            item9_positive=True,
            risk_level=result.risk_level,
            requires_safety_response=result.requires_safety_response,
            safety_response=crisis_text,
        )


def _label_for(severity_key: str | None) -> str | None:
    if not severity_key:
        return None
    labels = {
        "minimal": "Minimal",
        "mild": "Mild",
        "moderate": "Moderate",
        "moderately_severe": "Moderately severe",
        "severe": "Severe",
    }
    return labels.get(severity_key, severity_key)
