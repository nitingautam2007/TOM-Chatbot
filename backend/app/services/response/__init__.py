"""Local response generation (Phase 6) — curated library + lightweight selection.

No external AI APIs. Safety responses come from SafetyService (Phase 4), not
this package. This is not a clinical or diagnostic system.
"""

from app.services.response.library import (
    EMOTION_RESPONSES,
    FALLBACK_RESPONSES,
    INTENT_RESPONSES,
)
from app.services.response.selector import ResponseSelector, get_response_selector
from app.services.response.strategy import resolve_strategy
from app.services.response.types import (
    GeneratedResponse,
    ResponseContext,
    ResponseSource,
    Strategy,
)

__all__ = [
    "EMOTION_RESPONSES",
    "FALLBACK_RESPONSES",
    "INTENT_RESPONSES",
    "GeneratedResponse",
    "ResponseContext",
    "ResponseSource",
    "ResponseSelector",
    "Strategy",
    "get_response_selector",
    "resolve_strategy",
]
