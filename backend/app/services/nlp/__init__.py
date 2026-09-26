"""Local NLP foundation (Phase 3A) + prototype classification (Phase 3B).

Public surface:
- NLPService: orchestration (normalize → language → embed → NLPResult;
  classify → ClassificationResult with intent + emotion)
- EmbeddingService: lazy CPU-only multilingual sentence embeddings
- detect_language / normalize_text: standalone helpers
- IntentClassifier/EmotionClassifier helpers (classify_intent_text — the
  farewell-gated entry point; classify_intent is the raw scorer without the
  goodbye lexical gate)
- NLPResult / ClassificationResult: structured types (embedding never exposed)

Intent/emotion labels describe message content / expressed affect only —
they are not psychiatric diagnoses. Confidence scores are similarity-derived,
not calibrated clinical probabilities.
"""

from app.services.nlp.embeddings import EmbeddingService, get_embedding_service
from app.services.nlp.language import detect_language
from app.services.nlp.normalizer import normalize_text
from app.services.nlp.service import NLPService, get_nlp_service_singleton
from app.services.nlp.types import (
    ClassificationResult,
    EmotionResult,
    IntentResult,
    LanguageCode,
    LabelScore,
    NLPResult,
)
from app.services.nlp.emotion import classify_emotion
from app.services.nlp.intent import classify_intent, classify_intent_text

__all__ = [
    "ClassificationResult",
    "EmbeddingService",
    "EmotionResult",
    "IntentResult",
    "LabelScore",
    "LanguageCode",
    "NLPResult",
    "NLPService",
    "classify_emotion",
    "classify_intent",
    "classify_intent_text",
    "detect_language",
    "get_embedding_service",
    "get_nlp_service_singleton",
    "normalize_text",
]
