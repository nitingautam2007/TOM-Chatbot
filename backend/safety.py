#!/usr/bin/env python3
"""
TOM Safety Module
Deterministic safety interception and regional crisis hotline directory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DEFAULT_REGION = "IN"

REGION_LABELS = {
    "IN": "India",
    "US_CA": "US & Canada",
    "UK": "UK & Ireland",
    "INTL": "International",
}

CRISIS_RESPONSE = (
    "I'm really glad you told me. I want to make sure you're safe right now. "
    "If you are in immediate danger, please call your local emergency number. "
    "If you can, reach out to someone you trust and stay with them. "
    "You deserve support from a real person right now."
)

# Verified regional crisis hotlines and emergency contacts
CRISIS_RESOURCES: dict[str, list[dict[str, str]]] = {
    "IN": [
        {
            "label": "Tele-MANAS",
            "description": "Free, 24/7 national mental health helpline.",
            "tel": "14416",
        },
        {
            "label": "iCall",
            "description": "Free counselling, Monday to Saturday, 10am–8pm.",
            "tel": "+91-9152987821",
            "url": "https://icallhelpline.org",
        },
        {
            "label": "AASRA",
            "description": "24/7 crisis support and suicide prevention.",
            "tel": "+91-9820466726",
            "url": "http://www.aasra.info",
        },
        {
            "label": "Emergency services",
            "description": "If you are in immediate danger, call now.",
            "tel": "112",
        },
    ],
    "US_CA": [
        {
            "label": "988 Suicide & Crisis Lifeline",
            "description": "Call or text 988, free and confidential, 24/7 (US & Canada).",
            "tel": "988",
            "sms": "988",
        },
        {
            "label": "Crisis Text Line",
            "description": "US: text HOME to 741741. Canada: text CONNECT to 686868.",
            "url": "https://www.crisistextline.org",
        },
        {
            "label": "Emergency services",
            "description": "If you are in immediate danger, call 911.",
            "tel": "911",
        },
    ],
    "UK": [
        {
            "label": "Samaritans",
            "description": "Free, 24/7 listening support.",
            "tel": "116123",
            "url": "https://www.samaritans.org",
        },
        {
            "label": "Shout",
            "description": "Free, 24/7 text support. Text SHOUT to 85258.",
            "sms": "85258",
            "url": "https://giveusashout.org",
        },
        {
            "label": "Emergency services",
            "description": "If you are in immediate danger, call 999.",
            "tel": "999",
        },
    ],
    "INTL": [
        {
            "label": "Find A Helpline",
            "description": "Find a verified crisis line in your country.",
            "url": "https://findahelpline.com",
        },
        {
            "label": "Befrienders Worldwide",
            "description": "Find emotional support centres around the world.",
            "url": "https://befrienders.org",
        },
    ],
}

# Regex patterns for explicit self-harm, suicide, and overdose
_CRISIS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("self_harm", re.compile(r"\b(?:kill|killing)\s+(?:myself|my\s*self)\b")),
    (
        "self_harm",
        re.compile(
            r"\b(?:want|wanna|plan|planning|intend|intending|going|gonna|about)\s+"
            r"to\s+(?:kill|hurt|harm)\s+(?:myself|my\s*self)\b"
        ),
    ),
    (
        "suicide",
        re.compile(r"\b(?:commit|committing|attempt|attempted|attempting)\s+suicide\b"),
    ),
    ("suicide", re.compile(r"\bsuicid(?:e|al)\b")),
    ("suicide", re.compile(r"\b(?:end|ending)\s+my\s+life\b")),
    ("suicide", re.compile(r"\b(?:take|taking)\s+my\s+(?:own\s+)?life\b")),
    ("suicide", re.compile(r"\b(?:want|wish|wanting|wishing)\s+to\s+die\b")),
    (
        "suicide",
        re.compile(r"\b(?:don'?t|do\s+not)\s+want\s+to\s+(?:live|be\s+here|exist|go\s+on)\b"),
    ),
    (
        "suicide",
        re.compile(r"\b(?:better\s+off\s+dead|wish\s+i\s+(?:was|were)\s+dead|rather\s+be\s+dead)\b"),
    ),
    ("suicide", re.compile(r"\bno\s+reason\s+to\s+live\b")),
    ("suicide", re.compile(r"\blife\s+(?:is|isn'?t|is\s+not)\s+worth\s+living\b")),
    ("suicide", re.compile(r"\b(?:end\s+it\s+all|ending\s+it\s+all)\b")),
    ("suicide", re.compile(r"\b(?:tired\s+of\s+living|done\s+with\s+life)\b")),
    ("suicide", re.compile(r"\b(?:wish\s+i\s+wasn'?t\s+here|wish\s+i\s+wasn'?t\s+alive)\b")),
    ("self_harm", re.compile(r"\b(?:self[-\s]?harm|self[-\s]?harming)\b")),
    ("self_harm", re.compile(r"\b(?:cut|cutting)\s+(?:myself|my\s+wrists?)\b")),
    (
        "self_harm",
        re.compile(r"\b(?:hurt|hurting|harm|harming|injure|injuring)\s+(?:myself|my\s*self)\b"),
    ),
    ("self_harm", re.compile(r"\b(?:took|take|taking|had|have)\s+(?:an?\s+)?overdose\b")),
    ("self_harm", re.compile(r"\boverdosed\b")),
    (
        "self_harm",
        re.compile(
            r"\b(?:took|take|taking|swallowed)\s+(?:too\s+many|a\s+handful\s+of)\s+"
            r"(?:pills|tablets|meds|medication)\b"
        ),
    ),
    ("self_harm", re.compile(r"\b(?:hang|hanging)\s+(?:myself|my\s*self)\b")),
    ("self_harm", re.compile(r"\bkms\b")),
]

# Patterns for protective or negated statements to avoid false positives
_NEGATED_PATTERNS = [
    re.compile(r"\b(?:i\s+)?(?:do\s+not|don'?t)\s+want\s+to\s+die\b"),
    re.compile(r"\b(?:i\s+)?(?:do\s+not|don'?t)\s+want\s+to\s+kill\s+(?:myself|my\s*self)\b"),
    re.compile(r"\b(?:i\s+am|i'm|im)\s+not\s+suicidal\b"),
]


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase and stripping extra punctuation."""
    cleaned = text.lower().replace("’", "'")
    cleaned = re.sub(r"[^a-z0-9'\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalized_for_safety(text: str) -> str:
    return text.lower().replace("’", "'").strip()


def _remove_negated_protective_phrases(text: str) -> str:
    cleaned = text
    for pattern in _NEGATED_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


@dataclass(frozen=True)
class SafetyAssessment:
    is_crisis: bool
    reason: str | None = None
    response: str = CRISIS_RESPONSE
    resources: tuple[dict[str, Any], ...] = ()


def assess_safety(text: str) -> SafetyAssessment:
    """Evaluate text for crisis or self-harm keywords."""
    normalized = _normalized_for_safety(text)
    without_negations = _remove_negated_protective_phrases(normalized)

    for reason, pattern in _CRISIS_PATTERNS:
        if pattern.search(without_negations):
            return SafetyAssessment(is_crisis=True, reason=reason)

    return SafetyAssessment(is_crisis=False)


def detect_crisis(text: str) -> bool:
    return assess_safety(text).is_crisis


def get_crisis_resources(region: str | None = None) -> list[dict[str, Any]]:
    """Return crisis helpline numbers for the given region."""
    selected = region if region in CRISIS_RESOURCES else DEFAULT_REGION
    return [dict(resource) for resource in CRISIS_RESOURCES[selected]]


def get_region_label(region: str | None = None) -> str:
    selected = region if region in REGION_LABELS else DEFAULT_REGION
    return REGION_LABELS[selected]


__all__ = [
    "CRISIS_RESOURCES",
    "CRISIS_RESPONSE",
    "DEFAULT_REGION",
    "REGION_LABELS",
    "SafetyAssessment",
    "assess_safety",
    "detect_crisis",
    "get_crisis_resources",
    "get_region_label",
    "normalize_text",
]
