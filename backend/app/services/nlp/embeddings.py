"""Local multilingual sentence embedding service (CPU-only).

Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- Multilingual sentence embeddings (English / Hindi / Hinglish-friendly)
- ~110M params, CPU-friendly, no GPU required
- Output dimension read from the model at load time (expected 384)

Design:
- Lazy singleton: model loads once on first encode(), not at import time.
  FastAPI app import stays fast even if the model is missing/offline.
- Explicit device="cpu" — never uses GPU.
- Failures raise NLPUnavailableError (HTTP 503) — never crash the app process.
- Embeddings stay internal; only the dimension is exposed via NLPResult.

This is NOT a diagnostic model. Embeddings capture semantic similarity only.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

from app.core.config import settings
from app.services.errors import NLPUnavailableError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Load-once, CPU-only wrapper around sentence-transformers."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self._model_name = model_name or settings.embedding_model_name
        self._device = device or settings.embedding_device
        self._model = None
        self._dimension: int | None = None
        self._lock = threading.Lock()
        self._load_error: str | None = None

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------
    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if self._load_error is not None:
                raise NLPUnavailableError(self._load_error)
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "Loading embedding model %s on %s (CPU)…",
                    self._model_name,
                    self._device,
                )
                model = SentenceTransformer(
                    self._model_name,
                    device=self._device,
                )
                # Prefer the model's own reported dimension (sentence-transformers
                # 6.x: get_embedding_dimension; older: get_sentence_embedding_dimension).
                dimension: int | None = None
                for attr in ("get_embedding_dimension", "get_sentence_embedding_dimension"):
                    fn = getattr(model, attr, None)
                    if callable(fn):
                        dimension = int(fn())
                        break
                if dimension is None:
                    probe = model.encode(
                        ["dimension probe"],
                        normalize_embeddings=True,
                        convert_to_numpy=True,
                    )
                    dimension = int(np.asarray(probe).shape[-1])
                self._model = model
                self._dimension = dimension
                logger.info("Embedding model ready (dim=%d)", dimension)
            except Exception as exc:  # noqa: BLE001 — surface as controlled 503
                # Do not log full traceback with potential local paths to users;
                # log server-side only.
                logger.exception("Failed to load embedding model")
                self._load_error = (
                    f"Embedding model unavailable: {exc.__class__.__name__}. "
                    "Check that the model can be downloaded/cached locally."
                )
                raise NLPUnavailableError(self._load_error) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def dimension(self) -> int | None:
        """Model output dimension (None until the model has been loaded)."""
        if self._dimension is None and self._model is None:
            # Attempt load so dimension is available after first ensure.
            try:
                self._ensure_loaded()
            except NLPUnavailableError:
                return None
        return self._dimension

    def encode(self, text: str) -> np.ndarray:
        """Encode a single string → 1-D float32 numpy vector (normalized)."""
        return self.encode_batch([text])[0]

    def encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Encode a list of strings → list of 1-D float32 vectors (normalized)."""
        if not texts:
            return []
        self._ensure_loaded()
        assert self._model is not None
        try:
            vectors = self._model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            arr = np.asarray(vectors, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return [arr[i] for i in range(arr.shape[0])]
        except NLPUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Embedding encode failed")
            raise NLPUnavailableError(
                f"Embedding inference failed: {exc.__class__.__name__}"
            ) from exc


# Process-wide singleton (lazy). Tests may construct fresh instances.
_embedding_service: EmbeddingService | None = None
_singleton_lock = threading.Lock()


def get_embedding_service() -> EmbeddingService:
    """Return the shared EmbeddingService singleton (created on first call)."""
    global _embedding_service
    if _embedding_service is None:
        with _singleton_lock:
            if _embedding_service is None:
                _embedding_service = EmbeddingService()
    return _embedding_service
