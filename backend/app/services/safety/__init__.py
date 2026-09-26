"""Phase 4 — local safety / crisis-language detection (rule-based).

Public surface:
- SafetyService.detect(text) → SafetyResult
- get_safety_service_singleton()
- crisis_response(risk_level, language)

Risk labels are triage heuristics only — not clinical assessments.
Matches, scores, and pattern IDs stay internal (never in API responses).
"""

from app.services.safety.responses import crisis_response
from app.services.safety.service import SafetyService, get_safety_service_singleton
from app.services.safety.types import (
    RiskLevel,
    SafetyContextFlags,
    SafetyMatch,
    SafetyResult,
    SignalCategory,
)

__all__ = [
    "RiskLevel",
    "SafetyContextFlags",
    "SafetyMatch",
    "SafetyResult",
    "SafetyService",
    "SignalCategory",
    "crisis_response",
    "get_safety_service_singleton",
]
