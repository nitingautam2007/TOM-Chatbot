"""Phase 8 response strategy — pure, deterministic intent/emotion arbitration.

Safety never runs here: ChatService short-circuits on SafetyService before
ResponseSelector. This layer only answers "what kind of reply fits?"

Precedence (after safety):
1. Explicit farewell / greeting cues
2. Strong current emotional signal (incl. negation / temporal "now" state)
3. Polarity conflict: confident positive emotion vs mismatched intent
4. Aligned specific topical intent
5. Strong topical intent with weak/uncertain emotion
6. Confident non-aligned emotion (e.g. anger vs stress intent)
7. Confident intent alone / confident emotion alone
8. Lexical current-positive fallback → else strategy "fallback" (selector may
   try semantic retrieval, then generic fallback)

Not "emotion always wins": Phase 7 emotion accuracy ≈ 0.43, so emotion only
overrides when confident and in conflict with a weaker/mismatched intent.
"""

from __future__ import annotations

import re

from app.core.config import settings
from app.services.nlp.farewell import has_farewell
from app.services.nlp.negation import has_negation
from app.services.response.types import ResponseContext, Strategy

# Families for conflict detection (not diagnoses).
POSITIVE_EMOTIONS = frozenset({"happiness", "positive"})
NEGATIVE_AFFECT_EMOTIONS = frozenset(
    {"sadness", "anxiety", "stress", "anger", "loneliness"}
)
NEGATIVE_AFFECT_INTENTS = frozenset(
    {"sadness", "anxiety", "stress", "loneliness", "emotional_support"}
)
TOPICAL_INTENTS = frozenset(
    {
        "academic_pressure",
        "relationship_issue",
        "sleep_concern",
        "self_confidence",
        "coping_help",
        "help_seeking",
    }
)

# Emotion label → strategy (evaluation vocabulary).
EMOTION_STRATEGY: dict[str, Strategy] = {
    "sadness": "sadness_support",
    "anxiety": "anxiety_support",
    "stress": "stress_support",
    "loneliness": "loneliness_support",
    "anger": "anger_support",
    "happiness": "positive_affect",
    "positive": "positive_affect",
    "neutral": "neutral_conversation",
    "mixed": "clarification",
    "uncertain": "fallback",
}

# Intent label → strategy.
INTENT_STRATEGY: dict[str, Strategy] = {
    "greeting": "greeting",
    "goodbye": "farewell",
    "general_conversation": "neutral_conversation",
    "emotional_support": "sadness_support",
    "stress": "stress_support",
    "anxiety": "anxiety_support",
    "sadness": "sadness_support",
    "loneliness": "loneliness_support",
    "academic_pressure": "academic_support",
    "relationship_issue": "relationship_support",
    "sleep_concern": "sleep_support",
    "self_confidence": "encouragement",
    "coping_help": "coping_support",
    "help_seeking": "encouragement",
    "unknown": "clarification",
}

# Intent ↔ emotion same-family alignment for negative affect.
_ALIGNED: dict[str, frozenset[str]] = {
    "sadness": frozenset({"sadness"}),
    "anxiety": frozenset({"anxiety"}),
    "stress": frozenset({"stress"}),
    "loneliness": frozenset({"loneliness"}),
    "anger": frozenset({"anger"}),
    "emotional_support": frozenset({"sadness", "stress", "anxiety", "loneliness"}),
}

_DURATION_RE = re.compile(
    r"\b(long time|kaafi time|bahut time|kaafi din|for a long time|bahut din)\b",
    re.IGNORECASE,
)
_CONTRAST_RE = re.compile(
    r"\b(but|yet|now|actually|anymore|these days|today|abhi|aaj)\b",
    re.IGNORECASE,
)
_POS_LEX_RE = re.compile(
    r"\b(happy|glad|great|good|better|fine|hopeful|grateful|well|"
    r"khush|khushi|acha|accha|behtar|badhiya|theek)\b",
    re.IGNORECASE,
)
_NEG_STATE_RE = re.compile(
    r"\b(sad|down|low|anxious|worried|stressed|angry|lonely|udaas|dukh|"
    r"udasi|akela|ghabrahat)\b",
    re.IGNORECASE,
)
# "not happy" / "nahi khush" — positive word itself negated.
_NEGATED_POS_RE = re.compile(
    r"\b(not|n't|nahi|nahin|nhi)\s+(so\s+|very\s+|that\s+)?"
    r"(happy|glad|great|good|better|khush|accha|acha)\b",
    re.IGNORECASE,
)


def _intent_ok(context: ResponseContext) -> bool:
    intent = context.intent
    return (
        intent is not None
        and intent != "unknown"
        and intent in INTENT_STRATEGY
        and context.intent_confidence >= settings.intent_confidence_threshold
    )


def _emotion_ok(context: ResponseContext) -> bool:
    emotion = context.emotion
    return (
        emotion is not None
        and emotion != "uncertain"
        and context.emotion_confidence >= settings.emotion_confidence_threshold
    )


def suggests_current_positive(text: str) -> bool:
    """Lightweight current-state positive (negation / temporal contrast).

    Deterministic cues only — not a temporal NLP parser.
    """
    if not text:
        return False
    if _NEGATED_POS_RE.search(text):
        return False
    has_pos = bool(_POS_LEX_RE.search(text))
    if not has_pos:
        return False
    # Both polarities without a contrast cue → mixed, not "current positive".
    has_neg_state = bool(_NEG_STATE_RE.search(text))
    has_contrast = bool(_CONTRAST_RE.search(text))
    if has_pos and has_neg_state and not has_contrast and "anymore" not in text.lower():
        if not _NEGATED_POS_RE.search(text):
            # "happy and sad" — leave to mixed/clarification path.
            if re.search(r"\b(and|,|&)\b", text, re.IGNORECASE):
                return False
    # "not sad … happy" / "not lonely anymore"
    if has_negation(text) and _NEG_STATE_RE.search(text):
        return True
    if "anymore" in text.lower() and has_pos:
        return True
    # "was sad yesterday but today I feel better"
    if _CONTRAST_RE.search(text) and (_NEG_STATE_RE.search(text) or has_pos):
        # Contrast + positive word → prefer current positive when positive
        # word is present (exam went well, now better, …).
        if has_pos and (_NEG_STATE_RE.search(text) or _CONTRAST_RE.search(text)):
            return bool(has_pos)
    # Strong explicit positive without prior negative context still counts
    # when classifiers are weak — only if a first-person feeling cue exists.
    if re.search(
        r"\b(i am|i'm|i feel|feeling|feel|aaj|main)\b.{0,40}\b"
        r"(happy|glad|great|good|better|khush|acha|accha)\b",
        text,
        re.IGNORECASE,
    ):
        return True
    return False


def resolve_strategy(context: ResponseContext) -> Strategy:
    """Pick the conversational strategy for one message (pure / no I/O)."""
    raw = (context.message or "").strip()
    text = raw.lower()
    intent = context.intent or "unknown"
    emotion = context.emotion or "uncertain"
    intent_ok = _intent_ok(context)
    emotion_ok = _emotion_ok(context)

    # 1a. Explicit farewell cues (Phase 6 guards keep duration phrases out).
    if has_farewell(raw) or (intent == "goodbye" and intent_ok):
        return "farewell"

    # Duration phrases are not farewells — do not let weak emotion hijack them.
    if _DURATION_RE.search(text) and not has_farewell(raw):
        if not (emotion_ok and emotion in NEGATIVE_AFFECT_EMOTIONS):
            # Still allow a clear negative emotional message about "long time".
            if not (intent_ok and intent in NEGATIVE_AFFECT_INTENTS):
                return "clarification"

    # 1b. Greeting (do not erase multi-word emotional content).
    if intent == "greeting" and intent_ok:
        if emotion_ok and emotion in NEGATIVE_AFFECT_EMOTIONS and len(text.split()) > 4:
            return EMOTION_STRATEGY[emotion]
        return "greeting"

    # 2. Current positive state (negation / temporal) beats past-negative intent.
    if suggests_current_positive(text):
        if emotion in POSITIVE_EMOTIONS or emotion == "uncertain" or emotion_ok:
            if emotion not in NEGATIVE_AFFECT_EMOTIONS or emotion in POSITIVE_EMOTIONS:
                return "positive_affect"
        if intent in NEGATIVE_AFFECT_INTENTS or not intent_ok:
            return "positive_affect"

    # 2b. Explicit mixed affect → ask which thread, don't pick a family.
    if emotion_ok and emotion == "mixed":
        return "clarification"

    # 3. Confident positive emotion vs mismatched / generic intent.
    if emotion_ok and emotion in POSITIVE_EMOTIONS:
        return "positive_affect"

    # 6. Confident emotion that conflicts with a different negative intent family
    # (e.g. emotion=anger, intent=stress) → prefer the more specific emotion.
    if emotion_ok and intent_ok and emotion in NEGATIVE_AFFECT_EMOTIONS:
        if intent in NEGATIVE_AFFECT_INTENTS:
            aligned = emotion in _ALIGNED.get(intent, frozenset())
            if not aligned:
                # Emotion overrides mismatched intent when emotion is confident.
                return EMOTION_STRATEGY[emotion]
        elif intent in ("general_conversation", "unknown"):
            return EMOTION_STRATEGY[emotion]

    # 4. Topical intent (academic / relationship / sleep / …).
    if intent_ok and intent in TOPICAL_INTENTS:
        if emotion_ok and emotion in POSITIVE_EMOTIONS:
            return "positive_affect"
        return INTENT_STRATEGY[intent]

    # Aligned negative intent (+ optional emotion).
    if intent_ok and intent in NEGATIVE_AFFECT_INTENTS:
        if emotion_ok and emotion in POSITIVE_EMOTIONS:
            return "positive_affect"
        return INTENT_STRATEGY[intent]

    # Other confident intents (greeting already handled; general_conversation…).
    if intent_ok:
        return INTENT_STRATEGY.get(intent, "clarification")

    # 7. Confident emotion alone.
    if emotion_ok:
        return EMOTION_STRATEGY.get(emotion, "neutral_conversation")

    # Lexical current-positive when classifiers were uncertain.
    if suggests_current_positive(text):
        return "positive_affect"

    # 8. No reliable explicit signal → fallback (semantic then generic).
    return "fallback"
