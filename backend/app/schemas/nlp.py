"""Request/response schemas for NLP endpoints.

Phase 3A: /api/nlp/analyze
Phase 3B: /api/nlp/classify

Intent and emotion labels describe message content / expressed affect only.
They are not psychiatric diagnoses. Confidence scores are similarity-derived
internal estimates — not calibrated clinical probabilities.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NLPAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000, description="Raw user text to analyze")


class NLPAnalyzeResponse(BaseModel):
    language: str
    original_text: str
    normalized_text: str
    embedding_dimension: int
    processing_time_ms: float


class LabelScoreSchema(BaseModel):
    label: str
    score: float = Field(..., description="Similarity-derived score (not a calibrated probability)")


class IntentResultSchema(BaseModel):
    label: str = Field(..., description="Intent label; 'unknown' when below threshold/ambiguous")
    confidence_score: float = Field(
        ...,
        description="Cosine-prototype similarity in [0, 1]-ish range; NOT a clinical probability",
    )
    alternatives: list[LabelScoreSchema] = Field(default_factory=list)


class EmotionResultSchema(BaseModel):
    label: str = Field(..., description="Emotion label; 'uncertain' when below threshold/ambiguous")
    confidence_score: float = Field(
        ...,
        description="Cosine-prototype similarity; NOT a clinical probability",
    )
    alternatives: list[LabelScoreSchema] = Field(default_factory=list)


class NLPClassifyRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=4000, description="Raw user message to classify"
    )


class NLPClassifyResponse(BaseModel):
    original_text: str
    normalized_text: str
    language: str
    intent: IntentResultSchema
    emotion: EmotionResultSchema
    processing_time_ms: float
