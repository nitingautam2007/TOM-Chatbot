"""Emotion classification via prototype centroid cosine similarity (Phase 3B).

Describes expressed affect of a message — not a psychiatric diagnosis.
``confidence_score`` is similarity-derived, not a calibrated probability.
"""

from __future__ import annotations

import numpy as np

from app.core.config import settings
from app.services.errors import NLPUnavailableError
from app.services.nlp.negation import negation_penalty
from app.services.nlp.prototypes import PrototypeBank, get_emotion_bank
from app.services.nlp.scoring import is_low_content, pick_label
from app.services.nlp.types import EmotionResult


def classify_emotion(
    embedding: np.ndarray,
    normalized_text: str = "",
    bank: PrototypeBank | None = None,
) -> EmotionResult:
    """Return the best-matching emotion for ``embedding``.

    Applies lightweight negation damping, then falls back to ``uncertain``
    for low-content fillers, scores below threshold, or near-ties.
    """
    try:
        active_bank = bank or get_emotion_bank()
        scores = active_bank.score_all(embedding)
    except NLPUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface as 503
        raise NLPUnavailableError(
            f"Emotion classifier unavailable: {exc.__class__.__name__}"
        ) from exc

    if not scores:
        return EmotionResult(label="uncertain", confidence_score=0.0, alternatives=())

    if normalized_text:
        scores = {
            label: score * negation_penalty(label, normalized_text)
            for label, score in scores.items()
        }

    if is_low_content(normalized_text):
        top = max(scores.values(), default=0.0)
        return EmotionResult(
            label="uncertain", confidence_score=round(top, 4), alternatives=()
        )

    label, confidence, alternatives = pick_label(
        scores,
        threshold=settings.emotion_confidence_threshold,
        margin=settings.classification_ambiguity_margin,
        fallback="uncertain",
    )
    return EmotionResult(label=label, confidence_score=confidence, alternatives=alternatives)
