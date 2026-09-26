"""SafetyService — Phase 4 crisis-language detection (rule-based, local).

Pipeline: normalize → language detect → pattern match → context flags →
score → SafetyResult.

Constraints:
- Deterministic, CPU-only, no external AI APIs or ML models.
- Ephemeral: results are never persisted to PostgreSQL.
- Does not log the raw or normalized user message.
- Public callers must only surface risk_level / requires_safety_response /
  language / processing_time_ms / signal_categories.
"""

from __future__ import annotations

import re
import time
from dataclasses import replace

from app.services.errors import EmptyTextError
from app.services.nlp.language import detect_language
from app.services.nlp.normalizer import normalize_text
from app.services.safety.context import detect_context, strip_quoted_segments
from app.services.safety.detector import find_matches
from app.services.safety.responses import crisis_response
from app.services.safety.scoring import score_safety
from app.services.safety.types import SafetyResult

# Normalizer drops quote characters — detect them on the raw input.
_QUOTE_RE = re.compile(r"['\"“”].{0,200}?['\"“”]", re.DOTALL)


class SafetyService:
    """Ephemeral safety screening for a single message."""

    def detect(self, text: str, language: str | None = None) -> SafetyResult:
        """Screen ``text`` and return a SafetyResult (in-memory only)."""
        if not isinstance(text, str) or not text.strip():
            raise EmptyTextError()

        start = time.perf_counter()
        normalized = normalize_text(text)
        if not normalized:
            raise EmptyTextError()

        # Detect quotes on the raw string (normalizer strips them).
        raw_quoted = bool(_QUOTE_RE.search(text))

        # Quoted spans are stripped from matching but kept for context flags.
        searchable = strip_quoted_segments(normalized) or normalized
        context = detect_context(normalized)
        if raw_quoted:
            context = replace(context, quoted=True)

        lang = language or detect_language(normalized)
        if lang not in ("en", "hi", "hinglish", "unknown"):
            lang = "en"
        # Unknown script still gets English + any-language patterns.
        match_lang = lang if lang != "unknown" else "en"

        matches = find_matches(searchable, match_lang)
        risk, score, categories = score_safety(matches, context)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        requires = risk in ("high", "imminent") or (
            risk == "moderate"
            and any(m.category == "self_harm" for m in matches)
        )
        return SafetyResult(
            risk_level=risk,
            requires_safety_response=requires,
            language=lang,  # type: ignore[arg-type]
            processing_time_ms=elapsed_ms,
            signal_categories=categories,
            matches=matches,
            context=context,
            score=score,
        )

    def response_for(self, result: SafetyResult) -> str:
        """Non-clinical crisis reply for a HIGH/IMMINENT result."""
        return crisis_response(result.risk_level, result.language)


_service: SafetyService | None = None


def get_safety_service_singleton() -> SafetyService:
    """Process-wide SafetyService (stateless — rules are module-level)."""
    global _service
    if _service is None:
        _service = SafetyService()
    return _service
