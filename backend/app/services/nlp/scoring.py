"""Shared scoring helpers for Phase 3B prototype classifiers."""

from __future__ import annotations

import re

from app.services.nlp.types import LabelScore

_TOKEN_RE = re.compile(r"[a-zA-Z']+")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Vague backchannels / filler with no recoverable intent or emotion content.
# Always map to unknown / uncertain regardless of raw similarity.
LOW_CONTENT_TOKENS = frozenset(
    {
        "okay",
        "ok",
        "hmm",
        "hm",
        "mm",
        "mmm",
        "fine",
        "yeah",
        "yep",
        "yup",
        "nope",
        "nah",
        "k",
        "kk",
        "well",
        "uh",
        "um",
        "huh",
        "oh",
        "cool",
        "right",
        "whatever",
    }
)


def is_low_content(normalized_text: str) -> bool:
    """True for single short filler tokens (okay, hmm, fine, yeah, …)."""
    text = (normalized_text or "").strip()
    if not text:
        return True
    # Devanagari (Hindi) is never a Latin filler token.
    if _DEVANAGARI.search(text):
        return False
    tokens = [t for t in _TOKEN_RE.findall(text) if t]
    if not tokens:
        return False  # symbols only with no letters — leave to threshold path
    if len(tokens) > 2:
        return False
    return all(t in LOW_CONTENT_TOKENS for t in tokens)


def pick_label(
    scores: dict[str, float],
    threshold: float,
    margin: float,
    fallback: str,
) -> tuple[str, float, tuple[LabelScore, ...]]:
    """Choose top label or fall back when below threshold / ambiguous."""
    if not scores:
        return fallback, 0.0, ()

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_label, top_score = ranked[0]

    if top_score < threshold:
        return fallback, round(top_score, 4), ()

    if len(ranked) > 1 and (top_score - ranked[1][1]) < margin:
        return fallback, round(top_score, 4), ()

    alternatives = tuple(
        LabelScore(label=label, score=round(score, 4))
        for label, score in ranked[1:4]
    )
    return top_label, round(top_score, 4), alternatives
