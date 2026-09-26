"""Phase 3B public classifier surface (prototype, non-diagnostic)."""

from app.services.nlp.emotion import classify_emotion
from app.services.nlp.intent import classify_intent, classify_intent_text
from app.services.nlp.negation import has_negation, negation_penalty
from app.services.nlp.prototypes import (
    PrototypeBank,
    get_emotion_bank,
    get_intent_bank,
    reset_banks_for_tests,
)

__all__ = [
    "PrototypeBank",
    "classify_emotion",
    "classify_intent",
    "classify_intent_text",
    "get_emotion_bank",
    "get_intent_bank",
    "has_negation",
    "negation_penalty",
    "reset_banks_for_tests",
]
