"""Safe text normalization for TOM (Phase 3A).

Goals:
- collapse noisy whitespace
- lowercase Latin text (Devanagari has no case)
- keep meaningful punctuation lightly (sentiment/negation cues)
- preserve Unicode and Hindi text (including combining matras)
- NEVER remove stopwords or negation words ("not", "never", "don't", "nahi")

This is intentionally conservative — mental-health language depends on
negation and nuance. No stemming, no stopword deletion, no diagnosis.
"""

from __future__ import annotations

import re
import unicodedata

# Collapse runs of whitespace (including tabs/newlines) into single spaces.
_WHITESPACE = re.compile(r"\s+")

# Punctuation worth keeping for mental-health phrasing / emphasis.
_KEEP_PUNCT = frozenset("!?.,'-")


def _keep_char(ch: str) -> bool:
    """True for letters, numbers, marks (Devanagari matras), space, punct."""
    if ch.isspace():
        return True
    if ch in _KEEP_PUNCT:
        return True
    category = unicodedata.category(ch)
    # L* letters, N* numbers, M* marks (critical for Hindi combining signs).
    return category[0] in ("L", "N", "M")


def normalize_text(text: str) -> str:
    """Return a cleaned, lowercased, whitespace-collapsed string.

    Unicode is preserved: Devanagari letters and combining marks pass through
    unchanged aside from whitespace normalization. Empty/whitespace-only
    input returns "".
    """
    if not text:
        return ""

    cleaned = unicodedata.normalize("NFC", text)
    cleaned = "".join(ch for ch in cleaned if _keep_char(ch))
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    # lower() is a no-op for Devanagari; normalizes English/Hinglish matching.
    return cleaned.lower()
