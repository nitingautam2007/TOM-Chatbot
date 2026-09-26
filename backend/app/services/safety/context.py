"""Context overlays for safety scoring (Phase 4).

Handles negation, protective framing, person (first vs third), hypothetical /
quoted / reported speech, and past-vs-present reference so raw pattern hits
are not over- or under-weighted.

Rules are heuristic and explainable — not a full dependency parser. Limitations
are documented in docs/architecture.md.
"""

from __future__ import annotations

import re

from app.services.safety.types import SafetyContextFlags

# Reuse NLP negation cues when available; fall back to a local set.
_NEGATION_CUES = frozenset(
    {
        "not", "no", "never", "dont", "don't", "doesn't", "doesnt",
        "didn't", "didnt", "isn't", "isnt", "aren't", "arent",
        "wasn't", "wasnt", "weren't", "werent", "won't", "wont",
        "can't", "cant", "cannot", "without", "nahi", "nahin", "nhi",
        "mat", "anymore",
    }
)

_PROTECTIVE_CUES = frozenset(
    {
        "hope", "hopeful", "hopeless",  # "hopeless" handled below carefully
        "live", "living", "fighting", "fought",
        "reached", "help", "support", "safe", "staying",
        "better", "grateful", "thankful",
        "ummide", "ummid",
    }
)
# "hopeless" alone is not protective — remove pure-negation compounds.
_PROTECTIVE_CUES = _PROTECTIVE_CUES - {"hopeless"}

_THIRD_PERSON = re.compile(
    r"\b(he|she|they|him|her|his|hers|them|their|friend|mom|mother|father|"
    r"dad|brother|sister|someone|somebody|person|people|he's|she's)\b",
    re.IGNORECASE,
)

_HYPOTHETICAL = re.compile(
    r"\b(if|what\s+if|suppose|supposing|imagine|hypothetical|"
    r"pretend|were\s+to|would\s+if)\b",
    re.IGNORECASE,
)

_QUOTED = re.compile(r"['\"“”].{0,120}?['\"“”]", re.DOTALL)

_PAST = re.compile(
    r"\b(used\s+to|yesterday|last\s+(week|month|year|night)|"
    r"ago|previously|before|earlier|tried\s+to\s+end|"
    r"attempted)\b",
    re.IGNORECASE,
)

_FIRST_PERSON = re.compile(
    r"\b(i|i'm|i’ve|i've|im|me|my|mine|myself|मैं|मुझे|मेरा|मेरी|mere|mujh|mujhe|mera|meri)\b",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[a-zA-Zऀ-ॿ']+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def detect_context(normalized_text: str) -> SafetyContextFlags:
    """Return context flags for already-normalized (lowercased) text."""
    text = normalized_text or ""
    toks = _tokens(text)

    negated = bool(toks & _NEGATION_CUES)
    # Strong protective signals: explicit life preference or help-seeking.
    protective = bool(toks & _PROTECTIVE_CUES) or bool(
        re.search(
            r"\b(i\s+(want|choose|will)\s+to\s+live|"
            r"i\s+(will|won't|will\s+not)\s+(kill|end)\s+my|"
            r"there\s+is\s+hope)\b",
            text,
            re.IGNORECASE,
        )
    )
    # "I don't want to die" is protective via negation of ideation — also
    # count explicit "don't want to die" / "nahi marna" as protective.
    if re.search(r"\b(i\s+don't\s+want\s+to\s+(die|kill)|dont\s+want\s+to\s+(die|kill))\b",
                 text, re.IGNORECASE):
        protective = True
    if re.search(r"नहीं\s*(मर|marr)|नहीं\s*मारना|नहीं\s*मरना", text):
        protective = True

    third_person = bool(_THIRD_PERSON.search(text)) and not bool(
        _FIRST_PERSON.search(text)
    )
    # Pure third-person even when "I" appears (e.g. "my friend") → if only
    # friend/he/she dominate without first-person crisis subject, keep flag.
    if _THIRD_PERSON.search(text) and not _FIRST_PERSON.search(text):
        third_person = True
    elif re.search(r"\b(my\s+(friend|mom|mother|father|dad|brother|sister))\b",
                   text, re.IGNORECASE):
        third_person = True

    hypothetical = bool(_HYPOTHETICAL.search(text))
    quoted = bool(_QUOTED.search(normalized_text))  # quotes may be stripped — also check raw later
    past = bool(_PAST.search(text))

    return SafetyContextFlags(
        negated=negated,
        protective=protective,
        third_person=third_person,
        hypothetical=hypothetical,
        quoted=quoted,
        past_reference=past,
    )


def has_first_person(normalized_text: str) -> bool:
    return bool(_FIRST_PERSON.search(normalized_text or ""))


def strip_quoted_segments(text: str) -> str:
    """Remove double/single-quoted spans so reported speech is not scored as self."""
    if not text:
        return ""
    return _QUOTED.sub(" ", text)
