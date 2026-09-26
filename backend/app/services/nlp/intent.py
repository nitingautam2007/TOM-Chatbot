"""Intent classification via prototype centroid cosine similarity (Phase 3B).

Not a diagnosis and not a calibrated probability model. Labels describe
message content only.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.errors import NLPUnavailableError
from app.services.nlp.farewell import has_farewell
from app.services.nlp.prototypes import PrototypeBank, get_intent_bank
from app.services.nlp.scoring import is_low_content, pick_label
from app.services.nlp.types import IntentResult


def classify_intent(embedding, bank: PrototypeBank | None = None) -> IntentResult:
    """Return the best-matching intent for ``embedding``.

    Falls back to ``unknown`` for low-content fillers (okay/hmm/…), scores
    below threshold, or near-ties within the ambiguity margin.
    """
    try:
        active_bank = bank or get_intent_bank()
        scores = active_bank.score_all(embedding)
    except NLPUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface as 503
        raise NLPUnavailableError(
            f"Intent classifier unavailable: {exc.__class__.__name__}"
        ) from exc

    if not scores:
        return IntentResult(label="unknown", confidence_score=0.0, alternatives=())

    label, confidence, alternatives = pick_label(
        scores,
        threshold=settings.intent_confidence_threshold,
        margin=settings.classification_ambiguity_margin,
        fallback="unknown",
    )
    return IntentResult(label=label, confidence_score=confidence, alternatives=alternatives)


def classify_intent_text(
    embedding,
    normalized_text: str,
    bank: PrototypeBank | None = None,
) -> IntentResult:
    """Intent classification with a low-content / short-text guard."""
    if is_low_content(normalized_text):
        # Still score for transparency, but force unknown for fillers.
        try:
            active_bank = bank or get_intent_bank()
            scores = active_bank.score_all(embedding)
            top = max(scores.values(), default=0.0)
        except Exception:
            top = 0.0
        return IntentResult(label="unknown", confidence_score=round(top, 4), alternatives=())
    result = classify_intent(embedding, bank)
    # Goodbye needs explicit farewell evidence — duration phrases can score
    # high against goodbye centroids without being farewells. Explicit cues
    # (cya/ttyl/gtg) must win even when MiniLM prefers another centroid.
    if has_farewell(normalized_text):
        return IntentResult(
            label="goodbye",
            confidence_score=max(result.confidence_score, 0.5),
            alternatives=result.alternatives,
        )
    if result.label == "goodbye":
        return IntentResult(
            label="unknown",
            confidence_score=result.confidence_score,
            alternatives=(),
        )
    return result
