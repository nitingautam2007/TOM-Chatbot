"""Phase 6 response-generation types (local, non-diagnostic).

Internal only — confidence scores, selection metadata, and any retrieval
details are never exposed through the public API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.nlp.types import LanguageCode

ResponseSource = Literal[
    "safety",
    "context",
    "intent",
    "emotion",
    "semantic",
    "fallback",
]

# Phase 8 — what kind of conversational reply is appropriate (not the text).
Strategy = Literal[
    "greeting",
    "farewell",
    "positive_affect",
    "sadness_support",
    "anxiety_support",
    "stress_support",
    "loneliness_support",
    "anger_support",
    "academic_support",
    "relationship_support",
    "sleep_support",
    "coping_support",
    "encouragement",
    "clarification",
    "neutral_conversation",
    "safety_response",
    "fallback",
]


@dataclass(frozen=True, slots=True)
class ResponseContext:
    """Inputs for selecting one curated local reply.

    Intent/emotion labels describe message content / expressed affect only —
    not diagnoses. ``recent_messages`` is a small session window (newest
    last), never a long-term profile.
    """

    message: str
    language: LanguageCode = "unknown"
    intent: str | None = None
    intent_confidence: float = 0.0
    emotion: str | None = None
    emotion_confidence: float = 0.0
    recent_messages: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class GeneratedResponse:
    """Selected reply. Only ``text`` (and maybe language) is API-visible."""

    text: str
    source: ResponseSource
    language: LanguageCode
    is_safety: bool = False
    confidence: float | None = None  # internal selection score
    # Phase 10: which strategy produced this reply — used by ChatService to
    # set the additive `suggest_exercise` flag; never returned as-is.
    strategy: Strategy = "fallback"
