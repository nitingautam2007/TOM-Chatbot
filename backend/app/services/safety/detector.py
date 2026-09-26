"""Match normalized text against the Phase 4 crisis pattern inventory.

Pure function layer: no I/O, no logging of raw messages.
"""

from __future__ import annotations

from app.services.safety.patterns import CrisisPattern, patterns_for_language
from app.services.safety.types import SafetyMatch


def find_matches(normalized_text: str, language: str) -> tuple[SafetyMatch, ...]:
    """Return non-deduplicated matches (scoring takes the max base risk)."""
    if not normalized_text:
        return ()

    hits: list[SafetyMatch] = []
    patterns: tuple[CrisisPattern, ...] = patterns_for_language(language)
    for pattern in patterns:
        if pattern.regex.search(normalized_text):
            hits.append(
                SafetyMatch(
                    category=pattern.category,
                    base_risk=pattern.base_risk,
                    pattern_id=pattern.pattern_id,
                )
            )
    # Deduplicate identical pattern_ids (regex alternatives can double-fire).
    seen: set[str] = set()
    unique: list[SafetyMatch] = []
    for m in hits:
        if m.pattern_id in seen:
            continue
        seen.add(m.pattern_id)
        unique.append(m)
    return tuple(unique)
