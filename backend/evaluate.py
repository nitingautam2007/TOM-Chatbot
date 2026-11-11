#!/usr/bin/env python3
"""Grouped holdout evaluation for TOM's classifier.

Run from the backend directory:

    .venv/bin/python evaluate.py

The split is grouped by intent: at least one pattern per intent is held out
when the intent has enough patterns. Duplicate patterns across intents are kept
in the training side so the exact-match fast path cannot leak them into the
holdout.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path

from safety import normalize_text
from tom_chatbot import TOmChatbot

OFF_TOPIC_SAMPLES = [
    "What is 2+2?",
    "Can you write Python code?",
    "I like pizza",
    "The weather is nice today",
    "Tell me a joke about cats",
    "What time is the match tonight?",
    "I am dieting",
    "My phone battery is low",
]

FAQ_SAMPLES = [
    "What causes mental illness?",
    "what is depression",
    "How can I find a mental health professional?",
    "What is the difference between anxiety and stress?",
]


def grouped_split(
    samples: list[tuple[str, str]],
    holdout_ratio: float = 0.2,
    min_group_size: int = 3,
    seed: int = 42,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split samples by intent, keeping duplicates out of the holdout."""

    grouped: dict[str, list[str]] = defaultdict(list)
    for pattern, tag in samples:
        if pattern not in grouped[tag]:
            grouped[tag].append(pattern)

    rng = random.Random(seed)
    train: list[tuple[str, str]] = []
    holdout: list[tuple[str, str]] = []

    for tag in sorted(grouped):
        patterns = sorted(grouped[tag])
        rng.shuffle(patterns)
        if len(patterns) >= min_group_size:
            holdout_count = max(
                1,
                min(len(patterns) - 1, round(len(patterns) * holdout_ratio)),
            )
        else:
            holdout_count = 0
        holdout.extend((pattern, tag) for pattern in patterns[:holdout_count])
        train.extend((pattern, tag) for pattern in patterns[holdout_count:])

    rng.shuffle(train)

    # A pattern shared by two intents could otherwise be an exact-match hit
    # even though it was held out for one of them.
    train_keys = {normalize_text(pattern) for pattern, _ in train}
    holdout = [
        (pattern, tag)
        for pattern, tag in holdout
        if normalize_text(pattern) not in train_keys
    ]
    return train, holdout


def evaluate(
    data_path: str = "data.json",
    holdout_ratio: float = 0.2,
    min_group_size: int = 3,
    seed: int = 42,
) -> dict:
    bot = TOmChatbot(data_path=data_path)
    if not bot.load_data():
        raise SystemExit("Could not load data.json")
    if not bot.train_model():
        raise SystemExit("Could not train the classifier")

    train, holdout = grouped_split(
        bot.training_samples,
        holdout_ratio=holdout_ratio,
        min_group_size=min_group_size,
        seed=seed,
    )

    if not holdout:
        raise SystemExit("No holdout samples were created.")

    # Train on the split and remove the exact-match fast path so the score
    # reflects the classifier plus similarity support, not memorised patterns.
    if not bot.train_model(train):
        raise SystemExit("Could not train the holdout classifier")
    bot.exact_matches = {}

    correct = 0
    unknown = 0
    confusion: Counter[tuple[str, str]] = Counter()
    per_intent_total: Counter[str] = Counter()
    per_intent_correct: Counter[str] = Counter()

    for pattern, expected in holdout:
        prediction = bot.classify(pattern, allow_faq=False)
        per_intent_total[expected] += 1
        if prediction.intent == expected:
            correct += 1
            per_intent_correct[expected] += 1
        elif prediction.intent == "unknown":
            unknown += 1
        else:
            confusion[(expected, prediction.intent)] += 1

    total = len(holdout)
    accuracy = correct / total if total else 0.0
    unknown_rate = unknown / total if total else 0.0

    off_topic_answered = 0
    for text in OFF_TOPIC_SAMPLES:
        prediction = bot.classify(text, allow_faq=False)
        if prediction.intent != "unknown":
            off_topic_answered += 1
            print(
                f"  off-topic miss: {text!r} -> "
                f"{prediction.intent} ({prediction.confidence:.3f})"
            )

    faq_hits = 0
    for text in FAQ_SAMPLES:
        prediction = bot.classify(text, allow_faq=True)
        if prediction.source == "faq":
            faq_hits += 1
        else:
            print(f"  FAQ miss: {text!r} -> {prediction.intent}")

    print("\n" + "=" * 62)
    print("TOM grouped holdout evaluation")
    print("=" * 62)
    print(f"Training samples      : {len(train)}")
    print(f"Holdout samples       : {total}")
    print(f"Holdout accuracy      : {accuracy:.1%} ({correct}/{total})")
    print(f"Unknown on holdout    : {unknown_rate:.1%} ({unknown}/{total})")
    print(
        f"Off-topic answered    : {off_topic_answered}/{len(OFF_TOPIC_SAMPLES)} "
        "(lower is better)"
    )
    print(f"FAQ questions matched : {faq_hits}/{len(FAQ_SAMPLES)}")

    if confusion:
        print("\nTop confusions:")
        for (expected, predicted), count in confusion.most_common(10):
            print(f"  {expected:22s} -> {predicted:22s} {count}")

    weak_intents = [
        (tag, per_intent_correct[tag], per_intent_total[tag])
        for tag in sorted(per_intent_total)
        if per_intent_total[tag] and per_intent_correct[tag] < per_intent_total[tag]
    ]
    if weak_intents:
        print("\nIntents with holdout misses:")
        for tag, hit, count in weak_intents:
            print(f"  {tag:22s} {hit}/{count}")
    print("=" * 62)

    return {
        "train": len(train),
        "holdout": total,
        "accuracy": accuracy,
        "unknown_rate": unknown_rate,
        "off_topic_answered": off_topic_answered,
        "faq_hits": faq_hits,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent / "data.json"),
        help="Path to data.json",
    )
    parser.add_argument("--holdout-ratio", type=float, default=0.2)
    parser.add_argument("--min-group-size", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    evaluate(
        data_path=args.data,
        holdout_ratio=args.holdout_ratio,
        min_group_size=args.min_group_size,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
