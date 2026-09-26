"""Request/response schemas for the Phase 4 safety endpoint.

Only triage-level fields are exposed: risk_level, requires_safety_response,
language, processing_time_ms, and signal_categories. Internal scores, pattern
matches, regexes, and weights are never part of the public contract.

Risk labels are rule-based screening heuristics — not clinical assessments
or diagnoses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SafetyDetectRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Raw user message to screen for crisis language.",
        examples=["I don't want to be alive anymore"],
    )
    language: str | None = Field(
        default=None,
        description="Optional language hint (en/hi/hinglish). Auto-detected when omitted.",
    )


class SafetyDetectResponse(BaseModel):
    risk_level: str = Field(
        ...,
        description="none | low | moderate | high | imminent (rule-based triage label).",
    )
    requires_safety_response: bool = Field(
        ...,
        description="True when the chat pipeline should return a crisis reply.",
    )
    language: str = Field(..., description="Detected or provided language code.")
    processing_time_ms: float = Field(..., description="Server-side detection latency.")
    signal_categories: list[str] = Field(
        default_factory=list,
        description=(
            "Coarse signal categories (e.g. suicide_ideation, death_wish). "
            "No scores, patterns, or matched text spans."
        ),
    )
