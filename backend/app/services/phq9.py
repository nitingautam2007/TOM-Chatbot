"""PHQ-9 questionnaire constants and pure scoring (Phase 5).

Structured depressive-symptom screening — NOT a diagnosis, NOT an ML model.
Standard 9 items, 0–27 total, standard severity bands. English wording is
concise and preserves the meaning of the standardized items.
"""

from __future__ import annotations

PHQ9_TYPE = "phq9"
PHQ9_TIMEFRAME = "Over the last 2 weeks"
PHQ9_TOTAL_QUESTIONS = 9
ANSWER_MIN = 0
ANSWER_MAX = 3

ANSWER_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "Not at all"),
    (1, "Several days"),
    (2, "More than half the days"),
    (3, "Nearly every day"),
)

QUESTIONS: tuple[str, ...] = (
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling asleep, staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things",
    "Moving or speaking much more slowly than usual, or being unusually restless or fidgety",
    "Thoughts that you would be better off dead, or of hurting yourself in some way",
)

DISCLAIMER = (
    "This screening result describes symptom severity on the PHQ-9. "
    "It does not by itself diagnose depression and should not replace "
    "evaluation by a qualified professional."
)

# Probe text for SafetyService when item 9 is positive. Frequency (1–3) is
# intentionally NOT encoded here — Phase 4 remains the authority on risk level.
ITEM9_SAFETY_PROBE = "I wish I was dead or I want to hurt myself"

_SEVERITY_BANDS: tuple[tuple[int, int, str, str], ...] = (
    # (min, max, key, label)
    (0, 4, "minimal", "Minimal"),
    (5, 9, "mild", "Mild"),
    (10, 14, "moderate", "Moderate"),
    (15, 19, "moderately_severe", "Moderately severe"),
    (20, 27, "severe", "Severe"),
)


def score_phq9(responses: dict[int, int] | list[int]) -> int:
    """Sum of the nine item responses (0–27). Pure arithmetic — no ML."""
    if isinstance(responses, list):
        if len(responses) != PHQ9_TOTAL_QUESTIONS:
            raise ValueError("PHQ-9 requires exactly 9 responses")
        return sum(responses)
    if sorted(responses) != list(range(1, PHQ9_TOTAL_QUESTIONS + 1)):
        raise ValueError("PHQ-9 requires responses for questions 1..9")
    return sum(responses[q] for q in range(1, PHQ9_TOTAL_QUESTIONS + 1))


def severity_band(score: int) -> tuple[str, str]:
    """Return (severity_key, severity_label) for a 0–27 total score."""
    if score < 0 or score > 27:
        raise ValueError("PHQ-9 score must be between 0 and 27")
    for low, high, key, label in _SEVERITY_BANDS:
        if low <= score <= high:
            return key, label
    raise ValueError(f"Unmapped PHQ-9 score: {score}")


def item9_value(responses: dict[int, int] | list[int]) -> int:
    """Response to item 9 (death / self-harm thoughts)."""
    if isinstance(responses, list):
        return responses[8]
    return responses[9]
