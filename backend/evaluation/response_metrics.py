"""Phase 8 response-strategy metrics (no sklearn, pure Python)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Sequence

from evaluation.metrics import accuracy, evaluate


def strategy_report(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> dict:
    return evaluate(y_true, y_pred, labels=list(labels) if labels else None)


def forbidden_violations(
    texts: Sequence[str],
    forbidden_lists: Sequence[tuple[str, ...]],
) -> list[dict]:
    """Return cases where the reply contains any forbidden substring."""
    out: list[dict] = []
    for i, (text, forbidden) in enumerate(zip(texts, forbidden_lists)):
        low = (text or "").lower()
        hits = [f for f in forbidden if f.lower() in low]
        if hits:
            out.append({"index": i, "hits": hits, "text": text})
    return out


def bucket_match(
    expected_intent_key: str | None,
    expected_emotion_key: str | None,
    source: str,
    reply_text: str,
    intent_variants: dict[str, dict[str, tuple[str, ...]]],
    emotion_variants: dict[str, dict[str, tuple[str, ...]]],
    fallback_variants: dict[str, tuple[str, ...]],
    language: str,
) -> bool:
    """True if the selected reply comes from an allowed library bucket.

    When both expected keys are None, semantic/fallback (or any curated line)
    is acceptable — only forbidden substrings are checked separately.
    """
    if expected_intent_key is None and expected_emotion_key is None:
        return True
    lang = language if language in ("en", "hi", "hinglish") else "en"
    allowed: set[str] = set()
    if expected_intent_key:
        allowed.update(intent_variants.get(expected_intent_key, {}).get(lang, ()))
    if expected_emotion_key:
        allowed.update(emotion_variants.get(expected_emotion_key, {}).get(lang, ()))
    allowed.update(fallback_variants.get(lang, ()))
    return reply_text in allowed


def slice_accuracy(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    tags: Sequence[tuple[str, ...]],
    tag: str,
) -> dict | None:
    idx = [i for i, t in enumerate(tags) if tag in t]
    if not idx:
        return None
    yt = [y_true[i] for i in idx]
    yp = [y_pred[i] for i in idx]
    return {"tag": tag, "n": len(idx), "accuracy": accuracy(yt, yp)}


def tag_breakdown(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    tags: Sequence[tuple[str, ...]],
    all_tags: Sequence[str],
) -> list[dict]:
    out: list[dict] = []
    for tag in all_tags:
        row = slice_accuracy(y_true, y_pred, tags, tag)
        if row is not None:
            out.append(row)
    return out


def strategy_confusion_counts(
    y_true: Sequence[str],
    y_pred: Sequence[str],
) -> dict[str, int]:
    return dict(Counter(f"{t}->{p}" for t, p in zip(y_true, y_pred) if t != p))
