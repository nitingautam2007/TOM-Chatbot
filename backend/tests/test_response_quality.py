"""Phase 8 — response-strategy quality and regression tests.

Primary bug: "I am feeling happy today" selected sadness copy because
intent_ok ran before emotion_ok. Strategy layer must prefer positive_affect.

Safety contract is covered in test_safety / test_evaluation — here we only
assert the selector never emits crisis-style copy for non-crisis messages.
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.response import (
    EMOTION_RESPONSES,
    INTENT_RESPONSES,
    ResponseContext,
    ResponseSelector,
    resolve_strategy,
)
from app.services.response.strategy import suggests_current_positive
from app.services.response.types import Strategy

selector = ResponseSelector()


def _ctx(
    message: str,
    *,
    language: str = "en",
    intent: str | None = None,
    intent_confidence: float = 1.0,
    emotion: str | None = None,
    emotion_confidence: float = 1.0,
    recent: tuple[str, ...] = (),
) -> ResponseContext:
    return ResponseContext(
        message=message,
        language=language,  # type: ignore[arg-type]
        intent=intent,
        intent_confidence=intent_confidence,
        emotion=emotion,
        emotion_confidence=emotion_confidence,
        recent_messages=recent,
    )


def _is_sadness_copy(text: str) -> bool:
    return any(
        text in variants.get("en", ())
        for key in ("sadness", "emotional_support")
        for variants in (INTENT_RESPONSES.get(key), EMOTION_RESPONSES.get(key))
        if variants
    ) or text in EMOTION_RESPONSES["sadness"]["en"]


# ---------------------------------------------------------------------------
# 1. Primary bug: happy message must not get sadness copy
# ---------------------------------------------------------------------------
def test_happy_today_not_sadness_response() -> None:
    """Reproduced Phase 8 bug: intent=sadness 0.565, emotion=happiness 0.779."""
    ctx = _ctx(
        "I am feeling happy today",
        intent="sadness",
        intent_confidence=0.565,
        emotion="happiness",
        emotion_confidence=0.779,
    )
    assert resolve_strategy(ctx) == "positive_affect"
    out = selector.generate(ctx)
    assert out.text in EMOTION_RESPONSES["happiness"]["en"]
    assert not _is_sadness_copy(out.text)
    assert out.source in {"emotion", "context"}


def test_positive_affect_beats_confident_negative_intent() -> None:
    ctx = _ctx(
        "I am feeling happy today",
        intent="sadness",
        intent_confidence=0.9,
        emotion="happiness",
        emotion_confidence=0.85,
    )
    assert resolve_strategy(ctx) == "positive_affect"
    out = selector.generate(ctx)
    assert out.text in EMOTION_RESPONSES["happiness"]["en"]


def test_hinglish_positive_not_sadness() -> None:
    ctx = _ctx(
        "main aaj bahut khush hoon",
        language="hinglish",
        intent="sadness",
        intent_confidence=0.55,
        emotion="happiness",
        emotion_confidence=0.82,
    )
    assert resolve_strategy(ctx) == "positive_affect"
    out = selector.generate(ctx)
    assert out.text in EMOTION_RESPONSES["happiness"]["hinglish"]


def test_hindi_positive_not_sadness() -> None:
    ctx = _ctx(
        "आज मैं बहुत खुश हूँ",
        language="hi",
        intent="emotional_support",
        intent_confidence=0.5,
        emotion="happiness",
        emotion_confidence=0.8,
    )
    assert resolve_strategy(ctx) == "positive_affect"
    out = selector.generate(ctx)
    assert out.text in EMOTION_RESPONSES["happiness"]["hi"]


# ---------------------------------------------------------------------------
# 2. Negation / temporal: "not sad anymore … happy"
# ---------------------------------------------------------------------------
def test_not_sad_anymore_happy_strategy() -> None:
    ctx = _ctx(
        "I am not sad anymore, I am happy now",
        intent="sadness",
        intent_confidence=0.75,
        emotion="happiness",
        emotion_confidence=0.6,
    )
    assert resolve_strategy(ctx) == "positive_affect"
    assert suggests_current_positive(ctx.message)


def test_was_sad_but_today_better() -> None:
    ctx = _ctx(
        "I was sad yesterday but today I feel better",
        intent="sadness",
        intent_confidence=0.7,
        emotion="happiness",
        emotion_confidence=0.7,
    )
    assert resolve_strategy(ctx) == "positive_affect"


def test_negated_positive_not_treated_as_positive() -> None:
    assert not suggests_current_positive("I am not happy with my marks")
    assert not suggests_current_positive("nahi khush hoon main")


# ---------------------------------------------------------------------------
# 3. Farewell / greeting / duration
# ---------------------------------------------------------------------------
def test_explicit_farewell_strategy() -> None:
    ctx = _ctx("bye for now", intent="goodbye", intent_confidence=0.93)
    assert resolve_strategy(ctx) == "farewell"
    out = selector.generate(ctx)
    assert out.text in INTENT_RESPONSES["goodbye"]["en"]


def test_duration_phrase_is_clarification_not_farewell() -> None:
    for phrase in ("long time se", "kaafi time se", "for a long time"):
        ctx = _ctx(phrase, intent="unknown", intent_confidence=0.2, emotion="uncertain", emotion_confidence=0.3)
        strategy = resolve_strategy(ctx)
        assert strategy != "farewell", phrase
        out = selector.generate(ctx)
        assert out.text not in INTENT_RESPONSES["goodbye"]["en"]


def test_greeting_wins_short_hello() -> None:
    ctx = _ctx("hello", intent="greeting", intent_confidence=0.95, emotion="neutral", emotion_confidence=0.7)
    assert resolve_strategy(ctx) == "greeting"


def test_greeting_does_not_wipe_multiword_sadness() -> None:
    ctx = _ctx(
        "hi I am feeling really sad today",
        intent="greeting",
        intent_confidence=0.55,
        emotion="sadness",
        emotion_confidence=0.8,
    )
    assert resolve_strategy(ctx) == "sadness_support"
    out = selector.generate(ctx)
    assert out.text in EMOTION_RESPONSES["sadness"]["en"] or out.text in INTENT_RESPONSES["sadness"]["en"]


# ---------------------------------------------------------------------------
# 4. Aligned negative families still use intent/emotion support
# ---------------------------------------------------------------------------
def test_sadness_intent_aligned() -> None:
    ctx = _ctx("I feel so sad and empty", intent="sadness", emotion="sadness")
    assert resolve_strategy(ctx) == "sadness_support"
    out = selector.generate(ctx)
    assert out.text in INTENT_RESPONSES["sadness"]["en"]


def test_anxiety_intent_aligned() -> None:
    ctx = _ctx("I keep worrying", intent="anxiety", emotion="anxiety")
    assert resolve_strategy(ctx) == "anxiety_support"
    out = selector.generate(ctx)
    assert out.text in INTENT_RESPONSES["anxiety"]["en"]


def test_anger_emotion_overrides_stress_intent() -> None:
    ctx = _ctx(
        "I am angry about this",
        intent="stress",
        intent_confidence=0.46,
        emotion="anger",
        emotion_confidence=0.66,
    )
    assert resolve_strategy(ctx) == "anger_support"
    out = selector.generate(ctx)
    assert out.text in EMOTION_RESPONSES["anger"]["en"]


def test_academic_topical_intent() -> None:
    ctx = _ctx("exams overwhelm me", intent="academic_pressure", emotion="stress")
    assert resolve_strategy(ctx) == "academic_support"
    out = selector.generate(ctx)
    assert out.text in INTENT_RESPONSES["academic_pressure"]["en"]


# ---------------------------------------------------------------------------
# 5. Fallback / uncertain
# ---------------------------------------------------------------------------
def test_uncertain_emotion_unknown_intent_falls_back() -> None:
    ctx = _ctx(
        "hm not sure",
        intent="unknown",
        intent_confidence=0.0,
        emotion="uncertain",
        emotion_confidence=0.9,
    )
    strategy = resolve_strategy(ctx)
    assert strategy in {"fallback", "clarification"}
    out = selector.generate(ctx)
    assert out.source in {"semantic", "fallback", "emotion"}


def test_low_confidence_never_reports_intent_source() -> None:
    out = selector.generate(
        _ctx("hm", intent="stress", intent_confidence=0.1, emotion="neutral", emotion_confidence=0.1)
    )
    assert out.source != "intent"
    assert out.text


def test_empty_message_safe() -> None:
    out = selector.generate(_ctx("   ", language="unknown"))
    assert out.text
    assert out.source in {"semantic", "fallback"}


# ---------------------------------------------------------------------------
# 6. Safety never reaches selector (contract echo) + no crisis copy leak
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected_requires",
    [
        ("I will kill myself", True),
        ("I want to hurt myself", True),
        ("I'm happy today but I want to hurt myself.", True),
        ("I want to die", False),  # moderate ideation alone → no requires
        ("hello", False),
        ("I am feeling happy today", False),
    ],
)
def test_safety_requires_contract_unchanged(text: str, expected_requires: bool) -> None:
    from app.services.safety.service import SafetyService

    result = SafetyService().detect(text)
    assert result.requires_safety_response is expected_requires


def test_selector_never_emits_crisis_keywords_for_normal_positive() -> None:
    out = selector.generate(
        _ctx(
            "I am feeling happy today",
            intent="sadness",
            intent_confidence=0.565,
            emotion="happiness",
            emotion_confidence=0.779,
        )
    )
    low = out.text.lower()
    for banned in ("kill", "suicide", "harm yourself", "end your life"):
        assert banned not in low


# ---------------------------------------------------------------------------
# 7. Library quality: happiness / positive ≥ 3 variants per language
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", ["happiness", "positive"])
@pytest.mark.parametrize("lang", ["en", "hi", "hinglish"])
def test_positive_library_variants_at_least_three(key: str, lang: str) -> None:
    variants = EMOTION_RESPONSES[key][lang]
    assert len(variants) >= 3, f"{key}/{lang} has {len(variants)}"


# ---------------------------------------------------------------------------
# 8. Strategy resolution is pure / deterministic
# ---------------------------------------------------------------------------
def test_resolve_strategy_deterministic() -> None:
    ctx = _ctx(
        "I am feeling happy today",
        intent="sadness",
        intent_confidence=0.565,
        emotion="happiness",
        emotion_confidence=0.779,
    )
    a = resolve_strategy(ctx)
    b = resolve_strategy(ctx)
    assert a == b == "positive_affect"


def test_strategy_covers_all_literals_or_fallback() -> None:
    # Exhaustive strategy labels must map to a bucket or semantic/fallback path.
    all_strategies: set[Strategy] = {
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
    }
    # resolve_strategy only returns a subset in practice; smoke known paths.
    cases = [
        (_ctx("hello", intent="greeting"), "greeting"),
        (_ctx("bye", intent="goodbye"), "farewell"),
        (
            _ctx("happy", intent="sadness", emotion="happiness"),
            "positive_affect",
        ),
        (_ctx("sad", intent="sadness", emotion="sadness"), "sadness_support"),
        (_ctx("worry", intent="anxiety", emotion="anxiety"), "anxiety_support"),
        (_ctx("stress", intent="stress", emotion="stress"), "stress_support"),
        (
            _ctx("alone", intent="loneliness", emotion="loneliness"),
            "loneliness_support",
        ),
        (
            _ctx("furious", intent="stress", emotion="anger"),
            "anger_support",
        ),
        (
            _ctx("exams", intent="academic_pressure", emotion="stress"),
            "academic_support",
        ),
        (
            _ctx("fighting", intent="relationship_issue"),
            "relationship_support",
        ),
        (_ctx("cannot sleep", intent="sleep_concern"), "sleep_support"),
        (_ctx("how to cope", intent="coping_help"), "coping_support"),
        (_ctx("doubt myself", intent="self_confidence"), "encouragement"),
        (_ctx("just hanging", intent="general_conversation"), "neutral_conversation"),
        (_ctx("???"), "fallback"),
    ]
    seen: set[str] = set()
    for ctx, expected in cases:
        got = resolve_strategy(ctx)
        assert got == expected, (ctx.message, got, expected)
        assert got in all_strategies
        seen.add(got)
    # We exercised most of the vocabulary (safety_response never reaches here).
    assert len(seen) >= 14


def test_settings_version() -> None:
    assert settings.version == "0.10.0-phase10"
