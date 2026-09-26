"""Phase 4 safety detection endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_safety_service
from app.schemas.safety import SafetyDetectRequest, SafetyDetectResponse
from app.services.errors import EmptyTextError
from app.services.safety import SafetyService

router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.post(
    "/detect",
    response_model=SafetyDetectResponse,
    summary="Screen message for crisis language (development)",
    description=(
        "Rule-based, local crisis-language screening (English / Hindi / "
        "Hinglish). Returns only a coarse risk level and signal categories — "
        "never internal scores, patterns, or matched spans. NOT a clinical "
        "assessment, diagnosis, or emergency service."
    ),
)
async def detect(
    request: SafetyDetectRequest,
    service: Annotated[SafetyService, Depends(get_safety_service)],
) -> SafetyDetectResponse:
    try:
        result = service.detect(request.message, request.language)
    except EmptyTextError:
        raise HTTPException(status_code=422, detail="Message must not be empty")

    return SafetyDetectResponse(
        risk_level=result.risk_level,
        requires_safety_response=result.requires_safety_response,
        language=result.language,
        processing_time_ms=result.processing_time_ms,
        signal_categories=list(result.signal_categories),
    )
