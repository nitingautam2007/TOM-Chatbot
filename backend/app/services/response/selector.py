"""Lightweight local response selection (Phase 6, strategy layer Phase 8).

Hierarchy (safety is handled by ChatService *before* this runs):
1. resolve_strategy → library bucket (intent / emotion), context-aware variant
2. semantic retrieval via existing MiniLM embeddings (lazy, cached index)
   only for fallback / clarification — skipped when emotion is confident
3. safe conversational fallback

Deterministic: variant choice depends only on recent context — no RNG, so
tests stay stable. CPU-conscious: the semantic index embeds one text per
intent×language once and only when the strategy has no curated bucket.
"""

from __future__ import annotations

import threading

import numpy as np

from app.core.config import settings
from app.services.nlp.farewell import has_farewell
from app.services.nlp.types import LanguageCode
from app.services.response.library import (
    EMOTION_RESPONSES,
    FALLBACK_RESPONSES,
    INTENT_RESPONSES,
)
from app.services.response.strategy import resolve_strategy
from app.services.response.types import GeneratedResponse, ResponseContext, Strategy

# Strategy → (intent keys, emotion keys) for curated-bucket selection.
# Intent preferred when confidence-gated match exists; else emotion.
_BUCKET_INTENTS: dict[Strategy, tuple[str, ...]] = {
    "greeting": ("greeting",),
    "farewell": ("goodbye",),
    "sadness_support": ("sadness", "emotional_support"),
    "anxiety_support": ("anxiety",),
    "stress_support": ("stress",),
    "loneliness_support": ("loneliness",),
    "academic_support": ("academic_pressure",),
    "relationship_support": ("relationship_issue",),
    "sleep_support": ("sleep_concern",),
    "coping_support": ("coping_help",),
    "encouragement": ("self_confidence", "help_seeking"),
    "neutral_conversation": ("general_conversation",),
    "positive_affect": (),
    "anger_support": (),
    "clarification": (),
    "safety_response": (),
    "fallback": (),
}
_BUCKET_EMOTIONS: dict[Strategy, tuple[str, ...]] = {
    "positive_affect": ("happiness", "positive"),
    "sadness_support": ("sadness",),
    "anxiety_support": ("anxiety",),
    "stress_support": ("stress",),
    "loneliness_support": ("loneliness",),
    "anger_support": ("anger",),
    "neutral_conversation": ("neutral",),
    "clarification": ("mixed",),
    "greeting": (),
    "farewell": (),
    "academic_support": (),
    "relationship_support": (),
    "sleep_support": (),
    "coping_support": (),
    "encouragement": (),
    "safety_response": (),
    "fallback": (),
}


def _normalize_language(language: str | None) -> LanguageCode:
    if language in ("en", "hi", "hinglish"):
        return language  # type: ignore[return-value]
    return "en"


def _variants_for(
    library: dict[str, dict[str, tuple[str, ...]]],
    key: str,
    language: LanguageCode,
) -> tuple[str, ...]:
    return library.get(key, {}).get(language, ())


def _pick_variant(variants: tuple[str, ...], recent: tuple[str, ...]) -> str:
    """Deterministic context-aware pick: rotate with window length, skip repeats."""
    if not variants:
        return ""
    start = len(recent) % len(variants)
    for offset in range(len(variants)):
        candidate = variants[(start + offset) % len(variants)]
        if candidate not in recent:
            return candidate
    return variants[start % len(variants)]


class _SemanticIndex:
    """Lazy per-language cosine index over primary intent response texts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_lang: dict[str, tuple[list[str], np.ndarray]] = {}

    def match_intent(
        self,
        user_embedding: np.ndarray,
        language: str,
        threshold: float,
        *,
        skip_goodbye: bool = False,
    ) -> str | None:
        try:
            intents, matrix = self._ensure(language)
            if matrix.size == 0:
                return None
            scores = matrix @ user_embedding
            order = np.argsort(-scores)
            for idx in order:
                score = float(scores[idx])
                if score < threshold:
                    break
                intent = intents[int(idx)]
                if skip_goodbye and intent == "goodbye":
                    continue
                return intent
        except Exception:  # noqa: BLE001 — semantic path is optional
            return None
        return None

    def _ensure(self, language: str) -> tuple[list[str], np.ndarray]:
        cached = self._by_lang.get(language)
        if cached is not None:
            return cached
        with self._lock:
            cached = self._by_lang.get(language)
            if cached is not None:
                return cached
            intents = [
                key
                for key, by_lang in INTENT_RESPONSES.items()
                if language in by_lang and by_lang[language]
            ]
            texts = [INTENT_RESPONSES[key][language][0] for key in intents]
            if not texts:
                empty = ([], np.empty(0, dtype=np.float32))
                self._by_lang[language] = empty
                return empty
            from app.services.nlp.embeddings import get_embedding_service

            vectors = get_embedding_service().encode_batch(texts)
            matrix = np.stack(vectors).astype(np.float32, copy=False)
            entry = (intents, matrix)
            self._by_lang[language] = entry
            return entry


class ResponseSelector:
    """Selects one curated local reply from a ResponseContext."""

    def __init__(self) -> None:
        self._semantic = _SemanticIndex()

    def generate(self, context: ResponseContext) -> GeneratedResponse:
        language = _normalize_language(context.language)
        recent = context.recent_messages

        intent_key = context.intent if context.intent in INTENT_RESPONSES else None
        emotion_key = context.emotion if context.emotion in EMOTION_RESPONSES else None

        intent_ok = (
            intent_key is not None
            and intent_key != "unknown"
            and context.intent_confidence >= settings.intent_confidence_threshold
        )
        emotion_ok = (
            emotion_key is not None
            and emotion_key != "uncertain"
            and context.emotion_confidence >= settings.emotion_confidence_threshold
        )

        strategy = resolve_strategy(context)
        bucket = self._select_bucket(strategy, context, intent_ok, emotion_ok)
        if bucket is not None:
            library, key, base_source = bucket
            variants = _variants_for(library, key, language)
            if variants:
                # Repeated recent intent/emotion → still context-aware via rotation.
                source = "context" if any(v in recent for v in variants) else base_source
                conf = (
                    context.intent_confidence
                    if base_source == "intent"
                    else context.emotion_confidence
                )
                return GeneratedResponse(
                    text=_pick_variant(variants, recent),
                    source=source,  # type: ignore[arg-type]
                    language=language,
                    confidence=conf,
                    strategy=strategy,
                )

        # Fallback / clarification (or empty bucket): semantic only when emotion
        # is not confidently driving a different reply (avoid mismatch).
        if not emotion_ok:
            semantic_intent = self._semantic_match(context, language)
            if semantic_intent is not None:
                variants = _variants_for(INTENT_RESPONSES, semantic_intent, language)
                if variants:
                    return GeneratedResponse(
                        text=_pick_variant(variants, recent),
                        source="semantic",
                        language=language,
                        confidence=settings.response_semantic_threshold,
                        strategy=strategy,
                    )

        fallback = FALLBACK_RESPONSES.get(language) or FALLBACK_RESPONSES["en"]
        return GeneratedResponse(
            text=_pick_variant(fallback, recent),
            source="fallback",
            language=language,
            strategy=strategy,
        )

    @staticmethod
    def _select_bucket(
        strategy: Strategy,
        context: ResponseContext,
        intent_ok: bool,
        emotion_ok: bool,
    ) -> tuple[dict[str, dict[str, tuple[str, ...]]], str, str] | None:
        """Map strategy → (library, key, source) or None for semantic/fallback."""
        intent = context.intent or "unknown"
        emotion = context.emotion or "uncertain"
        intent_candidates = _BUCKET_INTENTS.get(strategy, ())
        emotion_candidates = _BUCKET_EMOTIONS.get(strategy, ())

        # Prefer confidence-gated intent (richer variants / topical specificity).
        if intent_ok:
            for key in intent_candidates:
                if key == intent and key in INTENT_RESPONSES:
                    return INTENT_RESPONSES, key, "intent"
        if emotion_ok:
            for key in emotion_candidates:
                if key == emotion and key in EMOTION_RESPONSES:
                    return EMOTION_RESPONSES, key, "emotion"
        # Strategy forced a label (e.g. positive_affect from lexical cue) —
        # still use first library match even if classifier was weak.
        for key in intent_candidates:
            if key == intent and key in INTENT_RESPONSES:
                return INTENT_RESPONSES, key, "intent"
        for key in emotion_candidates:
            if key == emotion and key in EMOTION_RESPONSES:
                return EMOTION_RESPONSES, key, "emotion"
        if strategy == "positive_affect" and "happiness" in EMOTION_RESPONSES:
            # Lexical current-positive with uncertain emotion label.
            if emotion not in EMOTION_RESPONSES or emotion == "uncertain":
                return EMOTION_RESPONSES, "happiness", "emotion"
        return None

    def _semantic_match(
        self, context: ResponseContext, language: LanguageCode
    ) -> str | None:
        threshold = settings.response_semantic_threshold
        if threshold <= 0:
            return None
        try:
            from app.services.nlp.embeddings import get_embedding_service

            text = (context.message or "").strip()
            if not text:
                return None
            embedding = get_embedding_service().encode(text)
            return self._semantic.match_intent(
                embedding,
                language,
                threshold,
                skip_goodbye=not has_farewell(text),
            )
        except Exception:  # noqa: BLE001 — model optional; fall back
            return None


_selector: ResponseSelector | None = None
_selector_lock = threading.Lock()


def get_response_selector() -> ResponseSelector:
    """Process-wide selector (semantic index still lazy per language)."""
    global _selector
    if _selector is None:
        with _selector_lock:
            if _selector is None:
                _selector = ResponseSelector()
    return _selector
