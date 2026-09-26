"""Development/testing endpoints for the Phase 3A/3B NLP layer."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_nlp_service
from app.schemas.nlp import (
    EmotionResultSchema,
    IntentResultSchema,
    LabelScoreSchema,
    NLPAnalyzeRequest,
    NLPAnalyzeResponse,
    NLPClassifyRequest,
    NLPClassifyResponse,
)
from app.services.errors import EmptyTextError, NLPUnavailableError
from app.services.nlp.service import NLPService

router = APIRouter(prefix="/api/nlp", tags=["nlp-dev"])


@router.post(
    "/analyze",
    response_model=NLPAnalyzeResponse,
    summary="Analyze text (development)",
    description=(
        "Runs local normalization, language detection (en/hi/hinglish), and "
        "multilingual sentence embedding. Returns metadata only — the "
        "embedding vector is never exposed. Development/testing endpoint; "
        "not a diagnostic tool."
    ),
)
async def analyze(
    request: NLPAnalyzeRequest,
    service: Annotated[NLPService, Depends(get_nlp_service)],
) -> NLPAnalyzeResponse:
    """Thin handler: validation via Pydantic, pipeline in NLPService."""
    try:
        result = service.process(request.text)
    except EmptyTextError:
        raise HTTPException(status_code=422, detail="Text must not be empty")
    except NLPUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return NLPAnalyzeResponse(
        language=result.language,
        original_text=result.original_text,
        normalized_text=result.normalized_text,
        embedding_dimension=result.embedding_dimension,
        processing_time_ms=result.processing_time_ms,
    )


@router.post(
    "/classify",
    response_model=NLPClassifyResponse,
    summary="Classify message intent + emotion (development)",
    description=(
        "Prototype intent and emotion classification via local cosine "
        "similarity over cached utterance embeddings (no external AI APIs, "
        "CPU-only). Labels describe message content or expressed affect — "
        "they are NOT psychiatric diagnoses. Confidence scores are "
        "similarity-derived internal estimates, NOT calibrated clinical "
        "probabilities. Development/testing endpoint."
    ),
)
async def classify(
    request: NLPClassifyRequest,
    service: Annotated[NLPService, Depends(get_nlp_service)],
) -> NLPClassifyResponse:
    try:
        result = service.classify(request.message)
    except EmptyTextError:
        raise HTTPException(status_code=422, detail="Message must not be empty")
    except NLPUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return NLPClassifyResponse(
        original_text=result.original_text,
        normalized_text=result.normalized_text,
        language=result.language,
        intent=IntentResultSchema(
            label=result.intent.label,
            confidence_score=result.intent.confidence_score,
            alternatives=[
                LabelScoreSchema(label=a.label, score=a.score)
                for a in result.intent.alternatives
            ],
        ),
        emotion=EmotionResultSchema(
            label=result.emotion.label,
            confidence_score=result.emotion.confidence_score,
            alternatives=[
                LabelScoreSchema(label=a.label, score=a.score)
                for a in result.emotion.alternatives
            ],
        ),
        processing_time_ms=result.processing_time_ms,
    )
