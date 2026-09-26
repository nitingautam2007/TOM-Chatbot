"""Lightweight, explainable negation cues for Phase 3B emotion damping.

Not a full negation scope parser. When a negation cue appears near an emotion
keyword, the corresponding class score is reduced so "I am not sad" is less
likely to land on ``sadness``. Limitations are documented in architecture docs.
"""

from __future__ import annotations

import re

# English + romanised-Hindi negation cues (normalized text is lowercased).
_NEGATION_CUES = frozenset(
    {
        "not",
        "no",
        "never",
        "dont",
        "don't",
        "doesn't",
        "doesnt",
        "didn't",
        "didnt",
        "isn't",
        "isnt",
        "aren't",
        "arent",
        "wasn't",
        "wasnt",
        "weren't",
        "werent",
        "won't",
        "wont",
        "can't",
        "cant",
        "cannot",
        "without",
        "nahi",
        "nahin",
        "nhi",
        "mat",
        "anymore",  # often paired with "not … anymore"
    }
)

# Keywords that, when negated, should dampen specific emotion scores.
# Key = emotion label; value = keyword tokens (already lower-case).
_NEGATED_EMOTION_KEYWORDS: dict[str, frozenset[str]] = {
    "sadness": frozenset(
        {"sad", "down", "low", "udaas", "dukh", "unhappy", "miserable"}
    ),
    "anxiety": frozenset(
        {"anxious", "worried", "worry", "nervous", "scared", "afraid", "ghabrahat", "tension"}
    ),
    "anger": frozenset({"angry", "mad", "furious", "irritate", "irritated", "gussa"}),
    "stress": frozenset({"stressed", "stress", "pressure", "overwhelmed", "tension"}),
    "loneliness": frozenset({"lonely", "alone", "akela", "akelapan"}),
    "happiness": frozenset({"happy", "glad", "khush", "great"}),
    "positive": frozenset({"hopeful", "better", "positive", "grateful"}),
}

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def has_negation(normalized_text: str) -> bool:
    """True when any known negation cue appears in the normalized text."""
    tokens = set(_tokens(normalized_text))
    return bool(tokens & _NEGATION_CUES)


def negation_penalty(emotion_label: str, normalized_text: str) -> float:
    """Return a multiplicative score penalty in (0, 1] for a negated emotion.

    Example: ``negation_penalty("sadness", "i am not sad")`` → 0.55 so a raw
    similarity that would have been 0.55 becomes ~0.30 (below typical threshold).
    """
    keywords = _NEGATED_EMOTION_KEYWORDS.get(emotion_label)
    if not keywords:
        return 1.0
    if not has_negation(normalized_text):
        return 1.0
    tokens = set(_tokens(normalized_text))
    if tokens & keywords:
        return 0.55
    return 1.0
