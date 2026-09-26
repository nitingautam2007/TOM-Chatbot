"""Aggregate pattern matches + context into a single risk level (Phase 4).

Deterministic scoring:
- start at ``none``
- raise risk to the max base_risk among active matches
- apply context caps (negation, third-person, hypothetical, quoted, past)
- protective context pulls risk down one step (not below ``none``)

``requires_safety_response`` is NOT computed here — SafetyService owns it
(backend/app/services/safety/service.py): True for high/imminent, or for
moderate risk when any match category is ``self_harm``.

Scores are internal — never returned by the public API.
"""

from __future__ import annotations

from app.services.safety.types import (
    RISK_ORDER,
    RiskLevel,
    SafetyContextFlags,
    SafetyMatch,
    SignalCategory,
)

# Cap risk when these context flags are present (max allowed level).
_CONTEXT_CAPS: dict[str, RiskLevel] = {
    "negated": "low",
    "third_person": "low",
    "hypothetical": "low",
    "quoted": "low",
    "past_reference": "moderate",  # past attempts still warrant caution
}

# Categories that stay actionable even under mild negation ("I don't want to
# die" still often signals distress) — handled via protective path instead.
_PROTECTIVE_DROP = 1
_HIGH_RISK = frozenset({"high", "imminent"})


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    return a if RISK_ORDER.index(a) >= RISK_ORDER.index(b) else b


def _raise(risk: RiskLevel, steps: int) -> RiskLevel:
    idx = min(RISK_ORDER.index(risk) + steps, len(RISK_ORDER) - 1)
    return RISK_ORDER[idx]


def _lower(risk: RiskLevel, steps: int) -> RiskLevel:
    idx = max(RISK_ORDER.index(risk) - steps, 0)
    return RISK_ORDER[idx]


def collect_categories(matches: tuple[SafetyMatch, ...],
                       context: SafetyContextFlags) -> tuple[SignalCategory, ...]:
    """Public-facing signal category list (order: risk-bearing first)."""
    order: list[SignalCategory] = []
    seen: set[str] = set()

    def add(cat: SignalCategory) -> None:
        if cat not in seen:
            seen.add(cat)
            order.append(cat)

    for m in matches:
        if m.base_risk in ("moderate", "high", "imminent"):
            add(m.category)
    for m in matches:
        if m.base_risk == "low":
            add(m.category)
    if context.negated:
        add("negation")
    if context.protective:
        add("protective_context")
    if context.hypothetical or context.quoted or context.third_person:
        add("ambiguous")
    return tuple(order)


def score_safety(
    matches: tuple[SafetyMatch, ...],
    context: SafetyContextFlags,
) -> tuple[RiskLevel, float, tuple[SignalCategory, ...]]:
    """Return ``(risk_level, internal_score, signal_categories)``."""
    risk: RiskLevel = "none"
    raw_score = 0.0

    for m in matches:
        if m.base_risk == "none":
            continue
        risk = _max_risk(risk, m.base_risk)
        raw_score += RISK_ORDER.index(m.base_risk) + 1.0

    # Context caps (first applicable wins in severity order).
    # Quoted / hypothetical / third-person content is not self-directed crisis.
    if context.quoted and risk != "none":
        risk = "low" if risk in ("moderate", "high", "imminent") else risk
    if context.hypothetical and risk in _HIGH_RISK | {"moderate"}:
        risk = "low"
    if context.third_person and risk in _HIGH_RISK | {"moderate"}:
        risk = "low"
    if context.negated and risk in _HIGH_RISK | {"moderate"}:
        # "I don't want to kill myself" / "nahi marna" → low unless plan+method
        if not any(
            m.category == "suicide_plan" and m.base_risk == "high"
            for m in matches
        ):
            risk = "low"
    if context.past_reference and risk == "imminent":
        risk = "high"
    if context.past_reference and risk == "high":
        # Past plan/intent is serious but not "present danger"
        risk = "moderate"

    if context.protective and risk != "none":
        risk = _lower(risk, _PROTECTIVE_DROP)

    # AMBIGUOUS topic-only mention with no other hits stays low.
    categories = collect_categories(matches, context)
    if risk == "none" and any(m.category == "ambiguous" for m in matches):
        risk = "low"

    return risk, raw_score, categories
