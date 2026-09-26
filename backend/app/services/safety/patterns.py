"""Crisis-language pattern inventory for Phase 4 safety detection.

Deterministic, explainable phrase/regex rules for English, Hindi (Devanagari),
and Hinglish (romanised Hindi). Patterns match surface language only — they do
not infer intent, diagnosis, or clinical risk.

Pattern notes:
- Matching runs on normalized text (lowercased, whitespace-collapsed).
- Multi-word phrases use flexible whitespace between tokens.
- Weights/base risk live with each pattern; scoring/context live in scoring.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.services.safety.types import RiskLevel, SignalCategory

PatternLanguage = Literal["en", "hi", "hinglish", "any"]


@dataclass(frozen=True, slots=True)
class CrisisPattern:
    pattern_id: str
    category: SignalCategory
    base_risk: RiskLevel
    regex: re.Pattern[str]
    languages: frozenset[PatternLanguage]


def _phrase(*tokens: str) -> str:
    """Join tokens into a flexible-whitespace phrase fragment."""
    return r"\s+".join(re.escape(t) for t in tokens)


def _compile(pattern_id: str, category: SignalCategory, base_risk: RiskLevel,
             expr: str, languages: set[PatternLanguage]) -> CrisisPattern:
    return CrisisPattern(
        pattern_id=pattern_id,
        category=category,
        base_risk=base_risk,
        regex=re.compile(expr, re.IGNORECASE),
        languages=frozenset(languages),
    )


_ANY = {"en", "hi", "hinglish", "any"}
_EN = {"en", "any"}
_HI = {"hi", "any"}
_HING = {"hinglish", "en", "any"}  # romanised phrases often read as en/hinglish

# ---------------------------------------------------------------------------
# IMMINENT — active danger / happening now (overrides HIGH when unmitigated)
# ---------------------------------------------------------------------------
_PATTERNS: tuple[CrisisPattern, ...] = (
    _compile(
        "imminent_kill_self_now",
        "imminent_danger",
        "imminent",
        r"\b(" + _phrase("kill", "myself", "now") + r"|"
        + _phrase("end", "it", "all", "now") + r"|"
        + _phrase("do", "it", "now") + r"|"  # alone is weak; paired check in scoring
        + _phrase("about", "to", "kill", "myself") + r"|"
        + _phrase("going", "to", "kill", "myself", "right", "now") + r")",
        _EN,
    ),
    _compile(
        "imminent_die_now",
        "imminent_danger",
        "imminent",
        r"\b(" + _phrase("want", "to", "die", "right", "now") + r"|"
        + _phrase("about", "to", "die", "tonight") + r"|"
        + _phrase("ending", "my", "life", "now") + r"|"
        + _phrase("end", "my", "life", "tonight") + r"|"
        + _phrase("kill", "myself", "tonight") + r"|"
        + _phrase("kill", "myself", "today") + r"|"
        + _phrase("kill", "myself", "this", "minute") + r")",
        _EN,
    ),
    _compile(
        "imminent_hindi",
        "imminent_danger",
        "imminent",
        r"(अभी|अब)\s*(मर|जान)\w*\s*(ना|ने|कर)|"
        r"अब\s*ख़त्म\s*कर\s*दूँ|"
        r"आज\s*रात\s*आत्महत्या|"
        r"अभी\s*आत्महत्या",
        _HI,
    ),
    _compile(
        "imminent_method_now",
        "imminent_danger",
        "imminent",
        r"\b(" + _phrase("swallowing", "pills", "now") + r"|"
        + _phrase("taking", "pills", "now") + r"|"
        + _phrase("jumping", "off", "now") + r"|"
        + _phrase("hanging", "myself", "now") + r")",
        _EN,
    ),
    # ---------------------------------------------------------------------------
    # HIGH — clear intent or plan (present/first person handled in context.py)
    # ---------------------------------------------------------------------------
    _compile(
        "intent_will_kill_self",
        "suicide_intent",
        "high",
        r"\b(" + _phrase("i", "will", "kill", "myself") + r"|"
        + _phrase("i", "am", "going", "to", "kill", "myself") + r"|"
        + _phrase("i'm", "going", "to", "kill", "myself") + r"|"
        + _phrase("i", "want", "to", "kill", "myself", "soon") + r"|"
        + _phrase("i", "plan", "to", "kill", "myself") + r"|"
        + _phrase("i", "plan", "to", "end", "my", "life") + r"|"
        + _phrase("i", "will", "end", "my", "life") + r")",
        _EN,
    ),
    _compile(
        "intent_die_soon_today",
        "suicide_intent",
        "high",
        r"\b(" + _phrase("i", "want", "to", "die", "soon") + r"|"
        + _phrase("i", "need", "to", "die", "today") + r"|"
        + _phrase("i", "will", "die", "tonight") + r"|"
        + _phrase("i'm", "going", "to", "die", "by", "suicide") + r")",
        _EN,
    ),
    _compile(
        "plan_concrete_method",
        "suicide_plan",
        "high",
        r"\b(" + _phrase("i", "have", "a", "plan", "to", "die") + r"|"
        + _phrase("i", "have", "a", "plan", "to", "kill", "myself") + r"|"
        + _phrase("bottle", "of", "pills") + r"|"
        + _phrase("wrote", "a", "suicide", "note") + r"|"
        + _phrase("written", "a", "suicide", "note") + r"|"
        + _phrase("rope", "and", "a", "chair") + r")",
        _EN,
    ),
    _compile(
        "intent_hindi",
        "suicide_intent",
        "high",
        r"मैं\s*आत्महत्या\s*करूँगा|"
        r"मैं\s*आत्महत्या\s*करूंगी|"
        r"मैं\s*मर\s*जाऊँगा|"
        r"मैं\s*मर\s*जाऊँगी|"
        r"आज\s*रात\s*मैं\s*मर\s*जाऊँ|"
        r"मैं\s*अपनी\s*जान\s*दे\s*दूँगा",
        _HI,
    ),
    _compile(
        "intent_hinglish",
        "suicide_intent",
        "high",
        r"\b(" + _phrase("main", "khudkushi", "karunga") + r"|"
        + _phrase("mai", "khudkushi", "karunga") + r"|"
        + _phrase("main", "marr", "jaunga") + r"|"
        + _phrase("mai", "marr", "jaunga") + r"|"
        + _phrase("kal", "main", "marr", "jaunga") + r")",
        _HING,
    ),
    # ---------------------------------------------------------------------------
    # MODERATE — active ideation / self-harm intent without a clear plan
    # ---------------------------------------------------------------------------
    _compile(
        "ideation_want_kill_self",
        "suicide_ideation",
        "moderate",
        r"\b(" + _phrase("i", "want", "to", "kill", "myself") + r"|"
        + _phrase("i", "wish", "i", "could", "kill", "myself") + r"|"
        + _phrase("thinking", "about", "killing", "myself") + r"|"
        + _phrase("i'm", "thinking", "about", "suicide") + r"|"
        + _phrase("i", "want", "to", "end", "my", "life") + r"|"
        + _phrase("i'm", "suicidal") + r"|"
        + _phrase("i", "am", "suicidal") + r")",
        _EN,
    ),
    _compile(
        "ideation_want_die",
        "suicide_ideation",
        "moderate",
        r"\b(" + _phrase("i", "want", "to", "die") + r"|"
        + _phrase("i", "wish", "i", "was", "dead") + r"|"
        + _phrase("i", "wish", "i", "were", "dead") + r"|"
        + _phrase("i", "don't", "want", "to", "be", "alive") + r"|"
        + _phrase("i", "dont", "want", "to", "be", "alive") + r"|"
        + _phrase("better", "if", "i", "wasn't", "born") + r"|"
        + _phrase("world", "would", "be", "better", "without", "me") + r")",
        _EN,
    ),
    _compile(
        "self_harm_ideation",
        "self_harm",
        "moderate",
        r"\b(" + _phrase("i", "want", "to", "hurt", "myself") + r"|"
        + _phrase("i", "want", "to", "cut", "myself") + r"|"
        + _phrase("urges", "to", "cut", "myself") + r"|"
        + _phrase("thinking", "about", "hurting", "myself") + r"|"
        + _phrase("i", "feel", "like", "hurting", "myself") + r"|"
        + _phrase("feeling", "like", "hurting", "myself") + r"|"
        + _phrase("i", "hurt", "myself", "again") + r"|"
        + _phrase("i'm", "cutting", "myself") + r"|"
        + _phrase("i", "am", "cutting", "myself") + r"|"
        + _phrase("self", "harm") + r"|"
        + _phrase("i", "burn", "myself") + r")",
        _EN,
    ),
    _compile(
        "ideation_hindi",
        "suicide_ideation",
        "moderate",
        r"मुझे\s*मर\s*जाना\s*है|"
        r"मैं\s*मर\s*जाना\s*चाहता|"
        r"मैं\s*मर\s*जाना\s*चाहती|"
        r"आत्महत्या\s*करने\s*का\s*मन\s*करता|"
        r"खुद\s*को\s*चोट\s*पहुँचाना\s*चाहता|"
        r"जीने\s*का\s*मन\s*नहीं\s*करता|"
        r"मुझे\s*मर\s*जाना\s*था|"
        r"मैं\s*मर\s*जाना\s*चाहता\s*था",
        _HI,
    ),
    _compile(
        "self_harm_hindi",
        "self_harm",
        "moderate",
        r"खुद\s*को\s*चोट\s*देनी|"
        r"खुद\s*को\s*चोट\s*देना|"
        r"खुद\s*को\s*नुकसान\s*पहुँचाना|"
        r"मैं\s*खुद\s*को\s*मार\s*लूँगा|"
        r"मैं\s*खुद\s*को\s*मार\s*लूँगी",
        _HI,
    ),
    _compile(
        "ideation_hinglish",
        "suicide_ideation",
        "moderate",
        r"\b(" + _phrase("mujhe", "marr", "jana", "hai") + r"|"
        + _phrase("main", "marr", "jana", "chahta") + r"|"
        + _phrase("mai", "marr", "jana", "chahta") + r"|"
        + _phrase("khudkushi", "karne", "ka", "mann", "karta") + r"|"
        + _phrase("jeene", "ka", "mann", "nahi", "karta") + r"|"
        + _phrase("khud", "ko", "hurt", "karna", "hai") + r"|"
        + _phrase("i", "wanted", "to", "die") + r"|"
        + _phrase("i", "wanted", "to", "kill", "myself") + r")",
        _HING,
    ),
    _compile(
        "self_harm_hinglish",
        "self_harm",
        "moderate",
        r"\b(" + _phrase("khud", "ko", "chot", "deni", "hai") + r"|"
        + _phrase("khud", "ko", "chot", "dena", "hai") + r"|"
        + _phrase("khud", "ko", "nuksan", "pahunchani", "hai") + r"|"
        + _phrase("khud", "ko", "hurt", "karna", "hai") + r")",
        _HING,
    ),
    _compile(
        "past_ideation_want_die",
        "suicide_ideation",
        "moderate",
        r"\b(" + _phrase("i", "wanted", "to", "die") + r"|"
        + _phrase("i", "wanted", "to", "kill", "myself") + r"|"
        + _phrase("i", "wished", "i", "was", "dead") + r")",
        _EN,
    ),
    # ---------------------------------------------------------------------------
    # LOW — death wish / passive ideation / topic-only mentions
    # ---------------------------------------------------------------------------
    _compile(
        "death_wish_passive",
        "death_wish",
        "low",
        r"\b(" + _phrase("sometimes", "i", "wish", "i", "was", "dead") + r"|"
        + _phrase("i", "wish", "i", "didn't", "exist") + r"|"
        + _phrase("i", "wish", "i", "didnt", "exist") + r"|"
        + _phrase("not", "sure", "i", "want", "to", "live") + r"|"
        + _phrase("don't", "see", "the", "point", "in", "living") + r"|"
        + _phrase("dont", "see", "the", "point", "in", "living") + r")",
        _EN,
    ),
    _compile(
        "topic_suicide_mention",
        "ambiguous",
        "low",
        r"\b(suicide|suicidal|khudkushi|आत्महत्या|self-kill)\b",
        _ANY,
    ),
    _compile(
        "death_wish_hinglish",
        "death_wish",
        "low",
        r"\b(" + _phrase("jeena", "nahi", "chahta") + r"|"
        + _phrase("jeena", "nahi", "chahti") + r"|"
        + _phrase("zindagi", "se", "tang", "aa", "gaya") + r")",
        _HING,
    ),
    # Past attempt / past ideation (still surfaces as a signal; scoring caps risk).
    _compile(
        "past_attempt_kill_self",
        "suicide_ideation",
        "moderate",
        r"\b(" + _phrase("tried", "to", "kill", "myself") + r"|"
        + _phrase("tried", "to", "end", "my", "life") + r"|"
        + _phrase("attempted", "suicide") + r"|"
        + _phrase("tried", "to", "die") + r"|"
        + _phrase("tried", "to", "hurt", "myself") + r"|"
        + _phrase("cut", "myself", "before") + r")",
        _EN,
    ),
    # ---------------------------------------------------------------------------
    # Protective / help-seeking phrases (reduce risk in scoring.py)
    # ---------------------------------------------------------------------------
    _compile(
        "protective_hope",
        "protective_context",
        "none",
        r"\b(" + _phrase("i", "want", "to", "live") + r"|"
        + _phrase("i", "choose", "to", "live") + r"|"
        + _phrase("i", "will", "keep", "fighting") + r"|"
        + _phrase("there", "is", "hope") + r"|"
        + _phrase("i", "will", "not", "kill", "myself") + r"|"
        + _phrase("i", "won't", "kill", "myself") + r"|"
        + _phrase("i", "reached", "out", "for", "help") + r")",
        _EN,
    ),
    _compile(
        "protective_hindi",
        "protective_context",
        "none",
        r"मुझे\s*जीना\s*है|"
        r"मैं\s*लड़ूँगा|"
        r"मैं\s*मदद\s*माँगूँगा|"
        r"उम्मीद\s*है",
        _HI,
    ),
)


def all_patterns() -> tuple[CrisisPattern, ...]:
    return _PATTERNS


def patterns_for_language(language: str) -> tuple[CrisisPattern, ...]:
    """Patterns whose language set includes ``language`` (plus ``any``)."""
    return tuple(p for p in _PATTERNS if language in p.languages)
