"""Prototype embedding bank + cosine scoring (Phase 3B).

Builds one embedding per example utterance once (lazy, cached), then scores
user embeddings with max-cosine over each class's examples. Designed so a
future supervised classifier can replace this without changing callers.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

from app.services.errors import NLPUnavailableError
from app.services.nlp.embeddings import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity for (assumed) L2-normalized vectors → float in [-1, 1]."""
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


class PrototypeBank:
    """Cached class-prototype embeddings for one taxonomy (intent or emotion)."""

    def __init__(
        self,
        examples: dict[str, tuple[str, ...]],
        embeddings: EmbeddingService | None = None,
    ) -> None:
        # Exclude labels with no examples (e.g. "unknown" / "uncertain").
        self._examples = {
            label: texts for label, texts in examples.items() if texts
        }
        self._embeddings = embeddings or get_embedding_service()
        self._vectors: dict[str, np.ndarray] | None = None
        self._lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._vectors is not None

    def _ensure_ready(self) -> dict[str, np.ndarray]:
        if self._vectors is not None:
            return self._vectors
        with self._lock:
            if self._vectors is not None:
                return self._vectors
            try:
                # Class centroid = mean of example embeddings, re-normalized.
                # More discriminative than max-cosine over individual examples
                # when classes share surface vocabulary (e.g. mental-health terms).
                centroids: dict[str, np.ndarray] = {}
                total = 0
                for label, texts in self._examples.items():
                    encoded = self._embeddings.encode_batch(list(texts))
                    matrix = np.stack(encoded, axis=0).astype(np.float32)
                    mean = matrix.mean(axis=0)
                    norm = float(np.linalg.norm(mean))
                    if norm > 0:
                        mean = mean / norm
                    centroids[label] = mean
                    total += matrix.shape[0]
                self._vectors = centroids
                logger.info(
                    "Prototype bank ready (%d classes, %d examples)",
                    len(centroids),
                    total,
                )
                return centroids
            except NLPUnavailableError:
                raise
            except Exception as exc:  # noqa: BLE001 — controlled 503
                logger.exception("Failed to build prototype embeddings")
                raise NLPUnavailableError(
                    f"Classifier prototypes unavailable: {exc.__class__.__name__}"
                ) from exc

    def score_all(self, embedding: np.ndarray) -> dict[str, float]:
        """Cosine similarity of ``embedding`` against each class centroid."""
        vectors = self._ensure_ready()
        query = np.asarray(embedding, dtype=np.float32).reshape(-1)
        q_norm = float(np.linalg.norm(query))
        if q_norm == 0:
            return {label: 0.0 for label in vectors}
        scores: dict[str, float] = {}
        for label, centroid in vectors.items():
            scores[label] = float(np.dot(centroid, query) / q_norm)
        return scores


# Process-wide caches keyed by id(examples dict) is fragile — use named banks.
_banks: dict[str, PrototypeBank] = {}
_banks_lock = threading.Lock()


def get_intent_bank(embeddings: EmbeddingService | None = None) -> PrototypeBank:
    from app.services.nlp.data.intent_examples import INTENT_EXAMPLES

    return _get_bank("intent", INTENT_EXAMPLES, embeddings)


def get_emotion_bank(embeddings: EmbeddingService | None = None) -> PrototypeBank:
    from app.services.nlp.data.emotion_examples import EMOTION_EXAMPLES

    return _get_bank("emotion", EMOTION_EXAMPLES, embeddings)


def _get_bank(
    name: str,
    examples: dict[str, tuple[str, ...]],
    embeddings: EmbeddingService | None,
) -> PrototypeBank:
    with _banks_lock:
        bank = _banks.get(name)
        if bank is None:
            bank = PrototypeBank(examples, embeddings)
            _banks[name] = bank
        return bank


def reset_banks_for_tests() -> None:
    """Clear cached prototype banks (tests only)."""
    with _banks_lock:
        _banks.clear()
