"""NLP orchestration service.

Phase 3A: normalize → language detect → embed → NLPResult.
Phase 3B: same pipeline plus intent + emotion prototype classification.
"""

from __future__ import annotations

import time

import numpy as np

from app.services.errors import EmptyTextError, NLPUnavailableError
from app.services.nlp.embeddings import EmbeddingService, get_embedding_service
from app.services.nlp.language import detect_language
from app.services.nlp.normalizer import normalize_text
from app.services.nlp.types import ClassificationResult, NLPResult


class NLPService:
    """Orchestrates the local NLP + classification pipeline (no external APIs)."""

    def __init__(self, embeddings: EmbeddingService | None = None) -> None:
        self._embeddings = embeddings

    def _embedding_service(self) -> EmbeddingService:
        return self._embeddings or get_embedding_service()

    def _analyze(self, text: str) -> tuple[NLPResult, np.ndarray]:
        if not isinstance(text, str) or not text.strip():
            raise EmptyTextError()

        start = time.perf_counter()
        normalized = normalize_text(text)
        if not normalized:
            raise EmptyTextError()

        language = detect_language(normalized) if normalized else "unknown"
        try:
            embedding = self._embedding_service().encode(normalized)
        except EmptyTextError:
            raise
        except NLPUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — controlled 503
            raise NLPUnavailableError(
                f"Embedding model unavailable: {exc.__class__.__name__}"
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        result = NLPResult(
            language=language,  # type: ignore[arg-type]
            original_text=text,
            normalized_text=normalized,
            embedding_dimension=int(embedding.shape[0]),
            processing_time_ms=elapsed_ms,
        )
        return result, embedding

    def process(self, text: str) -> NLPResult:
        """Phase 3A path: language + embedding (vector not returned)."""
        result, _ = self._analyze(text)
        return result

    def classify(self, message: str) -> ClassificationResult:
        """Phase 3B path: full classification (intent + emotion).

        Intent/emotion labels describe message content / expressed affect —
        they are NOT psychiatric diagnoses. Scores are similarity-derived
        internal estimates, not calibrated clinical probabilities.
        """
        start = time.perf_counter()
        nlp_result, embedding = self._analyze(message)

        # Deferred imports keep analyze-only usage from eagerly loading banks.
        from app.services.nlp.emotion import classify_emotion
        from app.services.nlp.intent import classify_intent_text

        intent = classify_intent_text(embedding, nlp_result.normalized_text)
        emotion = classify_emotion(embedding, nlp_result.normalized_text)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return ClassificationResult(
            language=nlp_result.language,
            original_text=nlp_result.original_text,
            normalized_text=nlp_result.normalized_text,
            intent=intent,
            emotion=emotion,
            processing_time_ms=elapsed_ms,
        )


_service: NLPService | None = None


def get_nlp_service_singleton() -> NLPService:
    """Process-wide NLPService (lazy model load on first use)."""
    global _service
    if _service is None:
        _service = NLPService()
    return _service
