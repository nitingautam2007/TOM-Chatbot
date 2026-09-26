"""Phase 5 — structured PHQ-9 depressive-symptom screening endpoints.

Screening, NOT diagnosis. Explicit workflow only (never auto-triggered from
chat). Session ownership uses the existing default-user mechanism.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_screening_service
from app.schemas.screening import (
    ScreeningAnswerRequest,
    ScreeningCompleteResponse,
    ScreeningStartResponse,
    ScreeningStateResponse,
)
from app.services.errors import ScreeningNotFoundError, ScreeningStateError
from app.services.screening_service import ScreeningService

router = APIRouter(prefix="/api/screening/phq9", tags=["screening"])


def _state_error(exc: ScreeningStateError) -> HTTPException:
    return HTTPException(status_code=409, detail=exc.detail)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Screening not found")


@router.post(
    "/start",
    response_model=ScreeningStartResponse,
    status_code=201,
    summary="Start a PHQ-9 screening session",
)
async def start(
    service: Annotated[ScreeningService, Depends(get_screening_service)],
) -> ScreeningStartResponse:
    try:
        return await service.start()
    except ScreeningStateError as exc:
        raise _state_error(exc)


@router.get(
    "/{screening_id}",
    response_model=ScreeningStateResponse,
    summary="Get current screening state",
)
async def get_state(
    screening_id: UUID,
    service: Annotated[ScreeningService, Depends(get_screening_service)],
) -> ScreeningStateResponse:
    try:
        return await service.state(screening_id)
    except ScreeningNotFoundError:
        raise _not_found()


@router.post(
    "/{screening_id}/answer",
    response_model=ScreeningStateResponse,
    summary="Submit one structured answer (0-3)",
)
async def answer(
    screening_id: UUID,
    request: ScreeningAnswerRequest,
    service: Annotated[ScreeningService, Depends(get_screening_service)],
) -> ScreeningStateResponse:
    try:
        return await service.answer(
            screening_id, request.question_number, request.answer
        )
    except ScreeningNotFoundError:
        raise _not_found()
    except ScreeningStateError as exc:
        raise _state_error(exc)


@router.post(
    "/{screening_id}/complete",
    response_model=ScreeningCompleteResponse,
    summary="Complete screening and return score/severity",
)
async def complete(
    screening_id: UUID,
    service: Annotated[ScreeningService, Depends(get_screening_service)],
) -> ScreeningCompleteResponse:
    try:
        return await service.complete(screening_id)
    except ScreeningNotFoundError:
        raise _not_found()
    except ScreeningStateError as exc:
        raise _state_error(exc)
