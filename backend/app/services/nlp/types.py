"""Shared result value types for Phase 3A NLP + Phase 3B classification.

Language codes and class labels are application-level annotations of surface
text — not medical or diagnostic categories. Embeddings are internal and
never returned through the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LanguageCode = Literal["en", "hi", "hinglish", "unknown"]

IntentLabel = Literal[
    "greeting",
    "goodbye",
    "general_conversation",
    "emotional_support",
    "stress",
    "anxiety",
    "sadness",
    "loneliness",
    "academic_pressure",
    "relationship_issue",
    "sleep_concern",
    "self_confidence",
    "coping_help",
    "help_seeking",
    "unknown",
]

EmotionLabel = Literal[
    "sadness",
    "anxiety",
    "anger",
    "stress",
    "loneliness",
    "happiness",
    "positive",
    "neutral",
    "mixed",
    "uncertain",
]


@dataclass(frozen=True, slots=True)
class NLPResult:
    """Structured output of NLPService.process().

    The embedding vector itself is intentionally not stored here for API
    exposure — only its dimension is reported. The vector stays internal to
    EmbeddingService for future classifiers.
    """

    language: LanguageCode
    original_text: str
    normalized_text: str
    embedding_dimension: int
    processing_time_ms: float


@dataclass(frozen=True, slots=True)
class LabelScore:
    """One scored class candidate (top label or alternative)."""

    label: str
    score: float


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Intent classification output.

    ``confidence_score`` is a similarity-derived internal estimate (cosine
    prototype score), **not** a calibrated clinical probability.
    """

    label: str
    confidence_score: float
    alternatives: tuple[LabelScore, ...]


@dataclass(frozen=True, slots=True)
class EmotionResult:
    """Emotion classification output (expressed affect, not a diagnosis).

    ``confidence_score`` is similarity-derived, not a clinical probability.
    """

    label: str
    confidence_score: float
    alternatives: tuple[LabelScore, ...]


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Full Phase 3B classification payload (no embedding vector)."""

    language: LanguageCode
    original_text: str
    normalized_text: str
    intent: IntentResult
    emotion: EmotionResult
    processing_time_ms: float
