"""Dedicated safety detection types (Phase 4).

Risk levels and signal categories are rule-based triage labels for crisis-language
screening only. They are NOT clinical assessments, diagnoses, or predictions.
Match details, weights, and internal scores are never exposed through the public API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.nlp.types import LanguageCode

RiskLevel = Literal["none", "low", "moderate", "high", "imminent"]

# Ordered weakest → strongest for aggregation.
RISK_ORDER: tuple[RiskLevel, ...] = ("none", "low", "moderate", "high", "imminent")

SignalCategory = Literal[
    "suicide_ideation",
    "self_harm",
    "death_wish",
    "suicide_intent",
    "suicide_plan",
    "imminent_danger",
    "self_harm_intent",
    "protective_context",
    "negation",
    "ambiguous",
]


@dataclass(frozen=True, slots=True)
class SafetyMatch:
    """One pattern hit with its base contribution (internal only)."""

    category: SignalCategory
    base_risk: RiskLevel
    pattern_id: str


@dataclass(frozen=True, slots=True)
class SafetyContextFlags:
    """Context overlays applied during scoring (internal only)."""

    negated: bool = False
    protective: bool = False
    third_person: bool = False
    hypothetical: bool = False
    quoted: bool = False
    past_reference: bool = False


@dataclass(frozen=True, slots=True)
class SafetyResult:
    """Full internal result of SafetyService.detect().

    ``risk_level`` and ``requires_safety_response`` are the only risk fields
    that may leave the service boundary. Matches, flags, and scores stay
    in-process (never logged with the raw message, never returned by the API).
    """

    risk_level: RiskLevel
    requires_safety_response: bool
    language: LanguageCode
    processing_time_ms: float
    signal_categories: tuple[SignalCategory, ...] = field(default=())
    matches: tuple[SafetyMatch, ...] = ()
    context: SafetyContextFlags = SafetyContextFlags()
    score: float = 0.0
