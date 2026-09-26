"""Minimal metric helpers for Phase 7 evaluation (no sklearn dependency)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Sequence


def confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> dict[str, dict[str, int]]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred length mismatch")
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    matrix: dict[str, dict[str, int]] = {
        t: {p: 0 for p in labels} for t in labels
    }
    for t, p in zip(y_true, y_pred):
        if t not in matrix:
            matrix[t] = {lab: 0 for lab in labels}
        if p not in matrix[t]:
            for row in matrix.values():
                row.setdefault(p, 0)
            matrix[t][p] = 0
            for row in matrix.values():
                row.setdefault(p, 0)
        matrix[t][p] = matrix[t].get(p, 0) + 1
    return matrix


def per_class_prf(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
) -> dict[str, dict[str, float | int]]:
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    support: Counter[str] = Counter(t for t in y_true)

    for t, p in zip(y_true, y_pred):
        if p == t:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1

    out: dict[str, dict[str, float | int]] = {}
    for label in labels:
        t, f_p, f_n = tp[label], fp[label], fn[label]
        precision = t / (t + f_p) if (t + f_p) else 0.0
        recall = t / (t + f_n) if (t + f_n) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        out[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support[label],
        }
    return out


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if not y_true:
        return 0.0
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return round(correct / len(y_true), 4)


def macro_weighted(
    per_class: dict[str, dict[str, float | int]],
    metric: str,
) -> tuple[float, float]:
    """Return (macro, weighted) averages for metric in {precision, recall, f1}."""
    present = [row for row in per_class.values() if row["support"]]
    if not present:
        return 0.0, 0.0
    macro = sum(float(row[metric]) for row in present) / len(present)
    total = sum(int(row["support"]) for row in present)
    weighted = (
        sum(float(row[metric]) * int(row["support"]) for row in present) / total
        if total
        else 0.0
    )
    return round(macro, 4), round(weighted, 4)


def evaluate(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> dict:
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    per_class = per_class_prf(y_true, y_pred, labels)
    macro_f1, weighted_f1 = macro_weighted(per_class, "f1")
    macro_p, weighted_p = macro_weighted(per_class, "precision")
    macro_r, weighted_r = macro_weighted(per_class, "recall")
    return {
        "n": len(y_true),
        "accuracy": accuracy(y_true, y_pred),
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
        "weighted_precision": weighted_p,
        "weighted_recall": weighted_r,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "confusion": confusion_matrix(y_true, y_pred, labels),
    }
