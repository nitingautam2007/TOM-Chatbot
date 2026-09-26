"""Shared explicit-farewell lexical cue (Phase 6 regression guard).

Goodbye intent and goodbye semantic retrieval must both see surface farewell
evidence — MiniLM alone places short duration phrases near goodbye prototypes.
"""

from __future__ import annotations

import re

# Explicit farewell cues (normalized / raw chat text, case-insensitive).
# Covers existing goodbye prototypes: bye, goodbye, see you later, phir milte,
# good night / goodnight, ok bye — plus see ya / see u variants.
_FAREWELL_RE = re.compile(
    r"\b("
    r"byebye"
    r"|bye+"
    r"|good[\s-]*bye"
    r"|see[\s-]+you"
    r"|see[\s-]+ya"
    r"|see[\s-]+u\b"
    r"|good[\s-]*night"
    r"|phir\s+milte"
    r"|alvida"
    r"|cya"
    r"|gtg"
    r"|ttyl"
    r")\b",
    re.IGNORECASE,
)


def has_farewell(text: str | None) -> bool:
    """True when ``text`` contains an explicit farewell cue."""
    if not text:
        return False
    return bool(_FAREWELL_RE.search(text))
