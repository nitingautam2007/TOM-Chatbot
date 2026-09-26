"""Request/response schemas for PHQ-9 screening (Phase 5).

Answers are strictly integers in {0,1,2,3}; question numbers in {1..9}.
No free-form text is accepted for scoring. Results are screening severity
bands — not diagnoses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ScreeningChoice(BaseModel):
    value: int
    label: str


class ScreeningStartResponse(BaseModel):
    """POST /api/screening/phq9/start."""

    screening_id: UUID
    screening_type: str
    status: str
    question_number: int
    total_questions: int
    timeframe: str
    question: str
    choices: list[ScreeningChoice]


class ScreeningAnswerRequest(BaseModel):
    """POST /api/screening/phq9/{id}/answer — strict integer validation."""

    question_number: Annotated[StrictInt, Field(ge=1, le=9)]
    answer: Annotated[StrictInt, Field(ge=0, le=3)]


class ScreeningSafetyStatus(BaseModel):
    """Coarse safety outcome when item 9 is positive (Phase 4 authority)."""

    item9_positive: bool
    risk_level: str
    requires_safety_response: bool
    safety_response: str | None = None


class ScreeningStateResponse(BaseModel):
    """GET /api/screening/phq9/{id} and answer-endpoint responses."""

    screening_id: UUID
    screening_type: str
    status: str
    total_questions: int
    timeframe: str
    answered_count: int
    question_number: int | None = None  # next/current question when in progress
    question: str | None = None
    choices: list[ScreeningChoice] | None = None
    complete_ready: bool = False
    score: int | None = None
    severity: str | None = None
    severity_label: str | None = None
    safety: ScreeningSafetyStatus | None = None
    disclaimer: str | None = None
    completed_at: datetime | None = None


class ScreeningCompleteResponse(BaseModel):
    """POST /api/screening/phq9/{id}/complete."""

    screening_id: UUID
    status: str
    score: int
    severity: str
    severity_label: str
    disclaimer: str
    safety: ScreeningSafetyStatus | None = None
    completed_at: datetime | None = None
