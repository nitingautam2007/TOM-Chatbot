"""Language / code-mix detection for English, Hindi, and Hinglish.

Phase 3A limitation notes:
- langdetect does NOT reliably understand Hinglish (romanised Hindi mixed
  with English). We therefore treat Hinglish as an **application-level**
  classification via a transparent heuristic on top of langdetect + script
  analysis — not a pretrained language ID model.
- This is NOT a clinical or diagnostic classifier. It only labels the surface
  form of the text for routing future NLP stages.
"""

from __future__ import annotations

import re
from functools import lru_cache

from langdetect import DetectorFactory, LangDetectException, detect

from app.services.nlp.types import LanguageCode

# Make langdetect deterministic across runs.
DetectorFactory.seed = 0

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN_WORD = re.compile(r"[A-Za-z']+")

# Distinctive romanised-Hindi tokens — words that almost never appear as
# ordinary English. Short/ambiguous function words (to, me, hi, par, se…)
# are intentionally EXCLUDED to avoid false Hinglish on pure English.
_DISTINCTIVE_HINGLISH = frozenset(
    {
        "mujhe", "mujh", "mera", "meri", "mere", "hume", "humein", "hamara",
        "aajkal", "bahut", "bohot", "kuch", "kuchh", "karne", "karna",
        "karta", "karti", "kare", "kiya", "kiye", "raha", "rahi", "rahe",
        "gaya", "gayi", "gaye", "lagta", "lagti", "lagte", "akela", "akeli",
        "nahi", "nahin", "nhi", "yaar", "bhai", "mann", "matlab", "bilkul",
        "theek", "thik", "zindagi", "hoon", "hain", "chahiye", "chahta",
        "chahti", "samajh", "samjh", "hamesha", "kabhi", "shayad", "kitna",
        "kitni", "kaisa", "kaisi", "kaise", "kyun", "kyu", "kya", "pata",
        "baar", "sach", "acha", "accha", "dost", "ghar", "raat", "subah",
        "shaam", "padhai", "liye", "liya", "dene", "dena", "leta", "leti",
        "hota", "hoti", "hote", "tumhe", "tumhara", "apna", "apni", "unka",
        "unki", "uska", "uski", "iska", "iski", "marna", "jeena", "sona",
        "jagna", "khana", "pani", "paani", "kaam", "office", "college",
        "result", "hamesha", "bina", "alag", "logon", "logo", "wala", "wali",
        "batata", "batati", "bataya", "samjha", "samjhi", "soch", "socha",
        "sochte", "dikkat", "pareshan", "tension", "akelapan", "udasi",
        "khushi", "dukh", "gham", "aansu", "neend", "bhook", "sehat",
        "dimag", "dimaag", "jazbaat", "ehsaas", "ehsaas", "mehsoos",
        "mahsoos", "takleef", "taklif", "dard", "ghav", "zakhm",
        "kaafi", "kafi", "haan", "haanji",
    }
)


def _has_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text))


def _latin_tokens(text: str) -> list[str]:
    return [t.lower() for t in _LATIN_WORD.findall(text) if t]


@lru_cache(maxsize=1024)
def _detect_base(text: str) -> LanguageCode:
    """langdetect result mapped to our codes; failures → script-based fallback."""
    if not text or not text.strip():
        return "unknown"
    try:
        code = detect(text)
    except LangDetectException:
        # Short inputs often raise — fall back to script analysis so common
        # English/Hindi sentences are not mislabeled "unknown".
        return _script_fallback(text)
    if code == "en":
        return "en"
    if code == "hi":
        return "hi"
    # Adjacent Indic outputs — only claim Hindi when Devanagari is present.
    if code in {"ur", "mr", "ne"} and _has_devanagari(text):
        return "hi"
    # langdetect sometimes mislabels very short English as other languages.
    if _looks_english(text):
        return "en"
    return _script_fallback(text)


def _looks_english(text: str) -> bool:
    """Heuristic: predominantly ASCII letters + common English stopwords."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    ascii_letters = sum(1 for ch in letters if ch.isascii())
    if ascii_letters / len(letters) < 0.9:
        return False
    tokens = _latin_tokens(text)
    common = {
        "i", "am", "is", "are", "was", "were", "be", "been", "being",
        "the", "a", "an", "and", "or", "but", "not", "no", "do", "does",
        "did", "feel", "feeling", "feels", "sad", "happy", "lonely",
        "stressed", "anxious", "tired", "you", "we", "they", "he", "she",
        "it", "my", "your", "our", "their", "this", "that", "these",
        "those", "have", "has", "had", "with", "without", "for", "to",
        "of", "in", "on", "at", "so", "very", "really", "just", "about",
        "today", "lately", "again", "still", "too", "all", "any", "can",
        "cant", "cannot", "wont", "dont", "cant", "never", "always",
    }
    if not tokens:
        return ascii_letters == len(letters)
    hits = sum(1 for t in tokens if t in common)
    return hits >= 1 or (len(tokens) <= 2 and ascii_letters == len(letters))


def _script_fallback(text: str) -> LanguageCode:
    """When langdetect fails: Devanagari → hi, Latin → en, else unknown."""
    if _has_devanagari(text):
        return "hi"
    if _looks_english(text):
        return "en"
    letters = [ch for ch in text if ch.isalpha()]
    if letters and all(ch.isascii() for ch in letters):
        # Latin-only but not confidently English — still more useful as en
        # than unknown for short chat messages; pure symbols stay unknown.
        return "en" if _latin_tokens(text) else "unknown"
    return "unknown"


def _hinglish_score(text: str) -> int:
    tokens = _latin_tokens(text)
    if not tokens:
        return 0
    return sum(1 for t in tokens if t in _DISTINCTIVE_HINGLISH)


def detect_language(text: str) -> LanguageCode:
    """Classify text as ``en``, ``hi``, ``hinglish``, or ``unknown``.

    Heuristic order:
    1. Empty / whitespace-only → unknown
    2. Substantial Devanagari → hi
    3. Latin script + enough *distinctive* romanised-Hindi tokens → hinglish
    4. Otherwise langdetect fallback (en / hi / unknown)
    """
    if not text or not text.strip():
        return "unknown"

    devanagari_chars = len(_DEVANAGARI.findall(text))
    latin_tokens = _latin_tokens(text)

    # Case 2: substantial Devanagari → Hindi.
    if devanagari_chars >= 2:
        return "hi"

    # Case 3: Latin script with clear romanised-Hindi signal → Hinglish.
    if latin_tokens:
        score = _hinglish_score(text)
        # ≥2 distinctive tokens is a strong signal; a single hit only counts
        # for very short utterances (≤5 tokens) to limit false positives.
        if score >= 2 or (score == 1 and len(latin_tokens) <= 5):
            return "hinglish"

    # Case 4: fall back to langdetect.
    base = _detect_base(text.strip())
    if base == "hi" and not _has_devanagari(text):
        # langdetect claimed Hindi but script is Latin → romanised Hindi we
        # didn't catch with the lexicon; report hinglish if Latin words exist.
        if latin_tokens:
            return "hinglish"
        return "unknown"
    return base
