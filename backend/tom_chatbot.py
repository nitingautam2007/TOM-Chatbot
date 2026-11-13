#!/usr/bin/env python3
"""
TOM - Talk To Me
Mental Health Support Chatbot
Using TF-IDF + Linear SVM Classifier with Safety Interception
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
from dataclasses import dataclass
from typing import Sequence

import nltk
import numpy as np
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

from safety import CRISIS_RESPONSE, assess_safety, normalize_text

# Crisis intents are handled by the safety layer, not the ML classifier
SAFETY_INTENTS = {"crisis", "suicide"}
SYNTHETIC_INTENT_PREFIX = "followup_"
UNKNOWN_INTENT = "unknown"

UNKNOWN_RESPONSE = (
    "I'm not sure I understood that. I'm here to listen if you want to talk "
    "about how you're feeling, or you can ask me about anxiety, sleep, coping, "
    "or finding support."
)

# Canonical intent mapping for synonyms and variations
INTENT_ALIASES = {
    "anxious": "anxiety",
    "coping_strategies": "coping",
    "death": "grief",
    "depressed": "depression",
    "evening": "greeting",
    "help": "coping",
    "learn-mental-health": "mental-health-fact",
    "morning": "greeting",
    "relationship_advice": "relationships",
    "sad": "sadness",
    "scared": "fear",
    "sleep_help": "sleep",
    "stressed": "stress",
    "worthless": "self_esteem",
}

FAQ_TAG_PREFIXES = ("fact-",)
FAQ_TAG_SUFFIXES = ("_info",)

QUESTION_STARTERS = {
    "are", "can", "could", "define", "did", "do", "does", "explain",
    "how", "is", "should", "was", "were", "what", "when", "where",
    "which", "who", "why", "will", "would",
}

# Confidence and similarity thresholds
FAQ_SIMILARITY_THRESHOLD = 0.40
CLASSIFIER_CONFIDENCE_THRESHOLD = 0.10
CLASSIFIER_AMBIGUITY_MARGIN = 0.025
CLASSIFIER_SUPPORT_OVERRIDE = 0.55
CLASSIFIER_SUPPORT_MINIMUM = 0.40

# Stop words tailored to preserve emotionally significant words
SUPPORT_STOP_WORDS = set(ENGLISH_STOP_WORDS) - {
    "alone", "cry", "down", "empty", "never", "no", "nobody",
    "none", "not", "nothing",
}

EMOTION_TAGS = {
    "anxiety", "depression", "fear", "happy", "loneliness",
    "mixed-feelings", "sadness", "stress",
}

FOLLOW_UP_QUESTIONS = [
    " Can you tell me more about that?",
    " How long have you been feeling this way?",
    " What do you think is causing this?",
    " Would you like to talk more about it?",
    " That's completely valid. What else is on your mind?",
]

# Ensure required NLTK resources are available
try:
    nltk.data.find("tokenizers/punkt")
    nltk.data.find("corpora/wordnet")
except LookupError:
    try:
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        nltk.download("wordnet", quiet=True)
    except Exception:
        nltk.download("popular", quiet=True)


def canonical_intent(tag: str) -> str:
    return INTENT_ALIASES.get(tag, tag)


def is_faq_intent(tag: str) -> bool:
    return tag.startswith(FAQ_TAG_PREFIXES) or tag.endswith(FAQ_TAG_SUFFIXES)


def is_synthetic_intent(tag: str) -> bool:
    return tag.startswith(SYNTHETIC_INTENT_PREFIX)


def is_classifier_intent(tag: str) -> bool:
    return (
        tag not in SAFETY_INTENTS
        and not is_faq_intent(tag)
        and not is_synthetic_intent(tag)
    )


@dataclass(frozen=True)
class FaqEntry:
    pattern: str
    response: str
    tag: str


@dataclass(frozen=True)
class Prediction:
    intent: str
    confidence: float
    source: str
    response: str | None = None


@dataclass(frozen=True)
class Reply:
    response: str
    intent: str
    confidence: float
    source: str


class TOmChatbot:
    """Mental health chatbot using TF-IDF feature extraction and SVM classification."""

    def __init__(self, data_path: str = "data.json"):
        self.data_path = data_path
        try:
            self.lemmatizer = WordNetLemmatizer()
        except Exception:
            self.lemmatizer = None

        self.intents: list[dict] = []
        self.raw_intents: list[dict] = []
        self.tags: list[str] = []
        self.patterns: list[str] = []
        self.responses: dict[str, list[str]] = {}
        self.model: Pipeline | None = None
        self.pattern_tags: list[str] = []
        self.model_trained = False
        self.conversation_history: list[tuple[str, str]] = []
        self.last_intent: str | None = None

        self.training_samples: list[tuple[str, str]] = []
        self.exact_matches: dict[str, str] = {}
        self.exact_conflicts: set[str] = set()
        self.faq_entries: list[FaqEntry] = []
        self.faq_vectorizer: TfidfVectorizer | None = None
        self.faq_matrix = None
        self.model_sample_count = 0

        self._training_patterns: list[str] = []
        self._training_tags: list[str] = []
        self._training_tokens: list[set[str]] = []
        self._training_matrix = None
        self._vocabulary: dict[str, int] = {}

    def _preprocess_text(self, text: str) -> list[str]:
        """Tokenize and lemmatize input text."""
        try:
            tokens = nltk.word_tokenize(text.lower())
        except Exception:
            tokens = re.findall(r"\b\w+\b", text.lower())

        try:
            if self.lemmatizer:
                lemmatized = []
                for token in tokens:
                    noun = self.lemmatizer.lemmatize(token, pos="n")
                    verb = self.lemmatizer.lemmatize(token, pos="v")
                    lemmatized.append(verb if len(verb) < len(noun) else noun)
                return lemmatized
        except Exception:
            pass
        return tokens

    def _content_tokens(self, text: str) -> set[str]:
        """Extract meaningful keywords for similarity comparison."""
        tokens = {
            token
            for token in self._preprocess_text(text)
            if len(token) > 1
            and token.isalpha()
            and token not in SUPPORT_STOP_WORDS
        }
        if re.search(r"\b(?:nobody|no\s*one|noone)\b", text.lower()):
            tokens.add("noone")
        return tokens

    def _nearest_support(
        self,
        text: str,
    ) -> tuple[float, str, float, float, int] | None:
        """Find the closest matching training pattern using cosine + jaccard overlap."""
        if (
            not self.model_trained
            or self.model is None
            or self._training_matrix is None
            or not self._training_tags
        ):
            return None

        query_tokens = self._content_tokens(text)
        if not query_tokens:
            return None

        vectorizer = self.model.named_steps["tfidf"]
        query_vector = vectorizer.transform([text])
        cosines = (self._training_matrix @ query_vector.T).toarray().ravel()

        best: tuple[float, str, float, float, int] | None = None
        for index, cosine in enumerate(cosines):
            if cosine <= 0:
                continue

            pattern_tokens = self._training_tokens[index]
            overlap = len(query_tokens & pattern_tokens)
            if overlap == 0:
                continue

            union_size = len(query_tokens | pattern_tokens)
            jaccard = overlap / union_size if union_size else 0.0
            strong_match = (
                overlap >= 2 and (jaccard >= 0.18 or cosine >= 0.35)
            ) or (
                overlap == 1
                and len(query_tokens) == 1
                and cosine >= 0.45
            )
            if not strong_match:
                continue

            score = (0.65 * float(cosine)) + (0.35 * jaccard)
            if best is None or score > best[0]:
                best = (
                    score,
                    self._training_tags[index],
                    float(cosine),
                    jaccard,
                    overlap,
                )

        return best

    def load_data(self) -> bool:
        """Load and parse training intents and FAQ from data.json."""
        try:
            with open(self.data_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            print(f"Error: Data file '{self.data_path}' not found!")
            return False
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in '{self.data_path}'")
            return False

        raw_intents = data.get("intents")
        if not isinstance(raw_intents, list):
            print("Error: data.json must contain an 'intents' list.")
            return False

        self.raw_intents = raw_intents
        merged: dict[str, dict] = {}
        merged_keys: dict[str, set[str]] = {}
        faq_by_key: dict[str, FaqEntry] = {}
        synthetic_count = 0

        for intent in raw_intents:
            if not isinstance(intent, dict):
                continue
            original_tag = str(intent.get("tag", "")).strip()
            if not original_tag:
                continue
            tag = canonical_intent(original_tag)
            patterns = [
                pattern.strip()
                for pattern in intent.get("patterns", [])
                if isinstance(pattern, str) and pattern.strip()
            ]
            responses = [
                response.strip()
                for response in intent.get("responses", [])
                if isinstance(response, str) and response.strip()
            ]

            if original_tag in SAFETY_INTENTS or tag in SAFETY_INTENTS:
                continue

            if is_synthetic_intent(original_tag):
                synthetic_count += 1
                continue

            if is_faq_intent(original_tag) or is_faq_intent(tag):
                for index, pattern in enumerate(patterns):
                    key = normalize_text(pattern) or pattern.lower()
                    if key in faq_by_key:
                        continue
                    response = (
                        responses[index % len(responses)]
                        if responses
                        else UNKNOWN_RESPONSE
                    )
                    faq_by_key[key] = FaqEntry(pattern, response, tag)
                continue

            entry = merged.setdefault(
                tag,
                {"tag": tag, "patterns": [], "responses": []},
            )
            seen_patterns = merged_keys.setdefault(tag, set())
            for pattern in patterns:
                key = normalize_text(pattern) or pattern.lower()
                if key in seen_patterns:
                    continue
                seen_patterns.add(key)
                entry["patterns"].append(pattern)
            for response in responses:
                if response not in entry["responses"]:
                    entry["responses"].append(response)

        self.intents = [
            entry for entry in merged.values() if entry["patterns"]
        ]
        self.tags = [entry["tag"] for entry in self.intents]
        self.responses = {
            entry["tag"]: entry["responses"] or [UNKNOWN_RESPONSE]
            for entry in self.intents
        }

        self.patterns = []
        self.pattern_tags = []
        for entry in self.intents:
            self.patterns.extend(entry["patterns"])
            self.pattern_tags.extend([entry["tag"]] * len(entry["patterns"]))
        self.training_samples = list(zip(self.patterns, self.pattern_tags))

        self.faq_entries = list(faq_by_key.values())
        self._build_faq_index()

        print(
            f"Loaded {len(self.intents)} classifier intents with "
            f"{len(self.training_samples)} patterns; "
            f"{len(self.faq_entries)} FAQ entries"
        )
        return True

    def _build_faq_index(self) -> None:
        """Build TF-IDF search index for factual questions."""
        if not self.faq_entries:
            self.faq_vectorizer = None
            self.faq_matrix = None
            return

        self.faq_vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.faq_matrix = self.faq_vectorizer.fit_transform(
            [entry.pattern for entry in self.faq_entries]
        )

    def train_model(
        self,
        samples: Sequence[tuple[str, str]] | None = None,
    ) -> bool:
        """Train the TF-IDF vectorizer + Linear SVM classifier pipeline."""
        training_samples = (
            list(self.training_samples) if samples is None else list(samples)
        )
        training_patterns: list[str] = []
        training_tags: list[str] = []
        for pattern, tag in training_samples:
            if not isinstance(pattern, str) or not pattern.strip():
                continue
            canonical_tag = canonical_intent(tag)
            if not is_classifier_intent(canonical_tag):
                continue
            training_patterns.append(pattern)
            training_tags.append(canonical_tag)

        if not training_patterns:
            print("No classifier training data available.")
            return False

        print("Training TOM's brain (TF-IDF + SVM)...")
        self.model = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        tokenizer=self._preprocess_text,
                        stop_words="english",
                        ngram_range=(1, 2),
                        sublinear_tf=True,
                    ),
                ),
                (
                    "clf",
                    SVC(
                        kernel="linear",
                        C=1.0,
                        random_state=42,
                        probability=True,
                    ),
                ),
            ]
        )

        self.exact_matches = {}
        self.exact_conflicts = set()
        for pattern, tag in zip(training_patterns, training_tags):
            key = normalize_text(pattern) or pattern.lower()
            if key in self.exact_matches and self.exact_matches[key] != tag:
                self.exact_conflicts.add(key)
                continue
            self.exact_matches[key] = tag

        self.model.fit(training_patterns, training_tags)
        self.model_trained = True
        self.model_sample_count = len(training_patterns)

        self._training_patterns = list(training_patterns)
        self._training_tags = list(training_tags)
        self._training_tokens = [
            self._content_tokens(pattern) for pattern in training_patterns
        ]
        self._training_matrix = self.model.named_steps["tfidf"].transform(
            training_patterns
        )
        self._vocabulary = self.model.named_steps["tfidf"].vocabulary_

        print(
            f"TOM trained with {len(training_patterns)} samples "
            f"across {len(self.model.classes_)} intents"
        )
        return True

    def _search_faq(self, text: str) -> tuple[FaqEntry, float] | None:
        """Search FAQ patterns using cosine similarity."""
        if (
            not self.faq_entries
            or self.faq_vectorizer is None
            or self.faq_matrix is None
        ):
            return None

        query = self.faq_vectorizer.transform([text])
        scores = (self.faq_matrix @ query.T).toarray().ravel()
        if scores.size == 0:
            return None

        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        if best_score < FAQ_SIMILARITY_THRESHOLD:
            return None
        return self.faq_entries[best_index], best_score

    @staticmethod
    def _looks_like_question(text: str) -> bool:
        stripped = text.strip().lower()
        if not stripped:
            return False
        if stripped.endswith("?"):
            return True
        match = re.match(r"[a-z']+", stripped)
        return bool(match and match.group(0) in QUESTION_STARTERS)

    def classify(
        self,
        text: str,
        check_safety: bool = True,
        allow_faq: bool = True,
    ) -> Prediction:
        """Classify user text and return predicted intent with confidence."""
        if not isinstance(text, str) or not text.strip():
            return Prediction(UNKNOWN_INTENT, 0.0, "unknown")

        # 1. Deterministic safety check
        if check_safety:
            assessment = assess_safety(text)
            if assessment.is_crisis:
                return Prediction(
                    "crisis",
                    1.0,
                    "safety",
                    assessment.response or CRISIS_RESPONSE,
                )

        # 2. Exact match lookup
        normalized = normalize_text(text)
        exact_tag = self.exact_matches.get(normalized)
        if exact_tag:
            return Prediction(exact_tag, 1.0, "exact")

        # 3. FAQ search for questions
        if allow_faq and self._looks_like_question(text):
            faq_match = self._search_faq(text)
            if faq_match:
                entry, score = faq_match
                return Prediction("faq", score, "faq", entry.response)

        if not self.model_trained or self.model is None:
            return Prediction(UNKNOWN_INTENT, 0.0, "unknown")

        content_tokens = self._content_tokens(text)
        if not content_tokens:
            return Prediction(UNKNOWN_INTENT, 0.0, "unknown")

        # 4. Out-of-vocabulary check
        vocabulary_candidates = {
            token
            for token in content_tokens
            if token not in ENGLISH_STOP_WORDS and token != "noone"
        }
        if vocabulary_candidates:
            out_of_vocabulary = sum(
                1
                for token in vocabulary_candidates
                if token not in self._vocabulary
            )
            if out_of_vocabulary / len(vocabulary_candidates) >= 0.5:
                return Prediction(UNKNOWN_INTENT, 0.0, "unknown")

        # 5. SVM probability prediction
        probabilities = self.model.predict_proba([text])[0]
        ranked = sorted(
            enumerate(probabilities),
            key=lambda item: item[1],
            reverse=True,
        )
        best_index, best_score = ranked[0]
        best_confidence = float(best_score)
        intent = str(self.model.classes_[best_index])
        second_confidence = float(ranked[1][1]) if len(ranked) > 1 else 0.0
        margin = best_confidence - second_confidence

        support = self._nearest_support(text)
        if support is not None:
            support_score, support_intent = support[0], support[1]
            support_score = min(0.99, support_score)
            if (
                support_intent == intent
                or best_confidence < CLASSIFIER_CONFIDENCE_THRESHOLD
                or support_score >= CLASSIFIER_SUPPORT_OVERRIDE
            ):
                return Prediction(support_intent, support_score, "similarity")

        if (
            best_confidence >= CLASSIFIER_CONFIDENCE_THRESHOLD
            and margin >= CLASSIFIER_AMBIGUITY_MARGIN
        ):
            return Prediction(intent, best_confidence, "classifier")

        if support is not None and support_score >= CLASSIFIER_SUPPORT_MINIMUM:
            return Prediction(support_intent, support_score, "similarity")

        return Prediction(UNKNOWN_INTENT, best_confidence, "unknown")

    def generate_reply(
        self,
        text: str,
        check_safety: bool = True,
        continuing: bool | None = None,
    ) -> Reply:
        """Classify input text and generate a conversational reply."""
        prediction = self.classify(text, check_safety=check_safety)

        if prediction.intent == "crisis":
            return Reply(
                prediction.response or CRISIS_RESPONSE,
                "crisis",
                1.0,
                "safety",
            )

        if prediction.source == "faq":
            return Reply(
                prediction.response or UNKNOWN_RESPONSE,
                "faq",
                prediction.confidence,
                "faq",
            )

        if prediction.intent == UNKNOWN_INTENT:
            return Reply(
                UNKNOWN_RESPONSE,
                UNKNOWN_INTENT,
                prediction.confidence,
                "unknown",
            )

        response = self._get_engaging_response(
            prediction.intent,
            text,
            continuing=continuing,
        )
        return Reply(
            response,
            prediction.intent,
            prediction.confidence,
            prediction.source,
        )

    def _get_response(self, tag: str, user_input: str = "") -> str:
        """Pick a curated response for the tag with optional follow-up questions."""
        tag = canonical_intent(tag)
        responses = self.responses.get(tag)
        if not responses:
            return random.choice(
                self.responses.get(
                    "none",
                    ["I'm here to listen. How can I help?"],
                )
            )

        if tag in EMOTION_TAGS:
            base_response = random.choice(responses)
            if not base_response.strip().endswith("?"):
                return base_response + random.choice(FOLLOW_UP_QUESTIONS)
            return base_response

        return random.choice(responses)

    def _get_engaging_response(
        self,
        intent: str,
        user_input: str,
        continuing: bool | None = None,
    ) -> str:
        """Add supportive prefixes and conversation continuity."""
        intent = canonical_intent(intent)

        if continuing is None:
            self.conversation_history.append((user_input, intent))
            self.last_intent = intent

            if len(self.conversation_history) > 5:
                self.conversation_history = self.conversation_history[-5:]

            continuing = len(self.conversation_history) > 1

        response = self._get_response(intent, user_input)

        if intent in {"sadness", "depression"}:
            prefix = (
                "I understand this is difficult for you."
                if continuing
                else "I'm here for you."
            )
            if prefix not in response:
                response = f"{prefix} {response}"
        elif intent in {"happy", "good", "fine"}:
            response = f"I'm so glad to hear that! {response}"

        return response

    def predict_intent(self, text: str, check_safety: bool = True) -> str:
        return self.classify(text, check_safety=check_safety).intent

    def respond(
        self,
        text: str,
        check_safety: bool = True,
        intent: str | None = None,
    ) -> str:
        if intent is None:
            return self.generate_reply(text, check_safety=check_safety).response

        if check_safety and assess_safety(text).is_crisis:
            return CRISIS_RESPONSE

        canonical = canonical_intent(intent)
        if canonical == UNKNOWN_INTENT:
            return UNKNOWN_RESPONSE
        if canonical == "faq":
            return self.generate_reply(text, check_safety=check_safety).response
        return self._get_engaging_response(canonical, text)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_welcome() -> None:
    clear_screen()
    print("=" * 60)
    print("  TOM - Talk To Me".center(60))
    print("  Your Mental Health Support Companion".center(60))
    print("=" * 60)
    print("\nHello! I'm TOM - Talk To Me.")
    print("I'm here to listen and support you.")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.\n")
    print("-" * 60)


def main() -> None:
    tom = TOmChatbot()

    if not tom.load_data():
        print("Failed to load data. Exiting...")
        sys.exit(1)

    tom.train_model()
    print_welcome()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
                print("\nTOM: Goodbye! Take care of yourself. I'm always here if you need to talk.")
                break

            if not user_input:
                continue

            response = tom.respond(user_input)
            print(f"\nTOM: {response}")

        except KeyboardInterrupt:
            print("\n\nTOM: Goodbye! Take care.")
            break
        except Exception as error:
            print(f"\nTOM: Sorry, I encountered an error: {error}")
            print("TOM: Let's try again. How can I help you?")


if __name__ == "__main__":
    main()
