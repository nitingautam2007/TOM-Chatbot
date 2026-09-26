"""Prepare TOM's emotion training data from the raw GoEmotions dataset.

DATA PREPARATION ONLY — this script never touches application code.
Run from backend/:

    cd backend
    .venv\\Scripts\\python -m evaluation.data.prepare_go_emotions

(Importing TOM's label list pulls in the app package, so production
requirements must be installed too — see backend/requirements.txt.)

Pipeline (each step is deliberately simple and auditable):

    load raw → validate → clean text → map labels to TOM's emotion taxonomy
    → drop duplicates (within and across splits) → write JSONL → print stats

Removal-reason counters are first-match: a row that is e.g. both unmapped and
a duplicate is counted only under its first failing check (output unaffected).

Output fields per record: text, label, source. Nothing else (no Reddit ids,
no usernames, no URLs added).

Multi-label handling: GoEmotions rows can carry several labels. A row is kept
only when every mapped label resolves to the SAME single TOM label; rows whose
labels resolve to nothing (unmapped) or to conflicting TOM labels are dropped
and counted. No label is ever invented.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from datasets import load_from_disk

# TOM's emotion taxonomy is owned by the app package — single source of truth.
from app.services.nlp.data import EMOTION_LABELS

# Project root: backend/evaluation/data/prepare_go_emotions.py -> parents[3]
ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "data" / "raw" / "go_emotions"
OUT_DIR = ROOT / "data" / "processed" / "go_emotions_tom"

SPLITS = ("train", "validation", "test")  # process order = leakage-guard order
SOURCE_NAME = "go_emotions"

# Approved GoEmotions -> TOM mapping (analysis: docs/dataset/go_emotions_analysis.md).
# None = label is deliberately IGNORED (no confident TOM equivalent).
# Every one of the 28 source labels appears here — nothing falls through.
GOEMOTIONS_TO_TOM: dict[str, str | None] = {
    "admiration": "positive",     # appreciation; no admiration bucket in TOM
    "amusement": "happiness",     # laughter/play delight
    "anger": "anger",             # direct
    "annoyance": "anger",         # mild irritation -> anger
    "approval": "positive",       # endorsement/support = warm positive affect
    "caring": "positive",         # warm affiliation -> broad positive
    "confusion": None,            # cognitive state, not affect
    "curiosity": None,            # cognitive state, not affect
    "desire": None,               # no TOM equivalent
    "disappointment": "sadness",  # let-down affect -> nearest TOM bucket
    "disapproval": None,          # rejection/evaluation of content, not felt
                                  # affect (unlike annoyance, which IS felt)
    "disgust": None,              # usually content-directed; no TOM bucket
    "embarrassment": None,        # self-conscious; not worry/sadness
    "excitement": "happiness",    # high-arousal positive
    "fear": "anxiety",            # fear/worry -> anxiety
    "gratitude": "positive",      # TOM positive prototype: "grateful today"
    "grief": "sadness",           # bereavement -> sadness
    "joy": "happiness",           # direct
    "love": "positive",           # warm affection; no love bucket in TOM
    "nervousness": "anxiety",     # direct
    "optimism": "positive",       # TOM positive prototype: "getting better"
    "pride": "positive",          # positive self-regard
    "realization": None,          # cognitive insight, not affect
    "relief": "positive",         # resolved tension = positive valence
    "remorse": None,              # guilt; no TOM equivalent (not sadness)
    "sadness": "sadness",         # direct
    "surprise": None,             # valence-ambiguous; no TOM bucket
    "neutral": "neutral",         # direct
}

_PLACEHOLDERS = {"[deleted]", "[removed]"}

# Identifiers are redacted, not content: third-party Reddit usernames
# ("u/x", "/u/x", any case) and social "@handles". Subreddit refs ("r/x")
# are kept — they are not personal data.
USERNAME_RE = re.compile(r"(?<!\w)/?u/[\w-]+|(?<![\w.@])@[\w-]{2,}", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Strip outer whitespace and collapse inner whitespace runs.

    Deliberately conservative: keeps case, punctuation, emoji and wording —
    that is real conversational signal for an emotion classifier.
    """
    return " ".join(text.split())


def resolve_tom_label(source_labels: list[str], names: list[str]) -> tuple[str | None, str]:
    """Map one row's GoEmotions labels to a single TOM label.

    Returns (label, reason): ("sadness", "ok") · (None, "unmapped") when no
    label maps · (None, "conflicting") when mapped labels disagree.
    """
    mapped = {GOEMOTIONS_TO_TOM[names[i]] for i in source_labels}
    mapped.discard(None)
    if len(mapped) == 1:
        return mapped.pop(), "ok"
    if not mapped:
        return None, "unmapped"
    return None, "conflicting"


def prepare(raw_dir: Path = RAW_DIR, out_dir: Path = OUT_DIR) -> dict:
    """Run the full pipeline. Returns a stats dict; writes one JSONL per split."""
    if not raw_dir.exists():
        raise SystemExit(
            f"Raw dataset not found: {raw_dir}\n"
            "Download it first (see data/raw/go_emotions/README.md)."
        )

    ds = load_from_disk(str(raw_dir))
    missing = [s for s in SPLITS if s not in ds]
    if missing:
        raise SystemExit(f"Raw dataset missing splits: {missing}")
    for split in SPLITS:
        cols = list(ds[split].features.keys())
        if cols != ["text", "labels", "id"]:
            raise SystemExit(f"Unexpected columns in {split}: {cols}")

    names: list[str] = list(ds["train"].features["labels"].feature.names)
    for split in SPLITS[1:]:
        if list(ds[split].features["labels"].feature.names) != names:
            raise SystemExit(f"Label order differs in split {split}")
    unknown = [n for n in names if n not in GOEMOTIONS_TO_TOM]
    if unknown:
        raise SystemExit(f"Dataset has labels not covered by the mapping: {unknown}")

    raw_label_counts = Counter()
    removed = Counter()
    redacted_rows = 0
    kept_with_ignored_label = 0
    kept_counts: dict[str, Counter] = {}
    seen: dict[str, set[str]] = {s: set() for s in SPLITS}
    seen_earlier: set[str] = set()

    out_dir.mkdir(parents=True, exist_ok=True)
    total_kept = 0

    for split in SPLITS:
        kept: list[dict] = []
        for row in ds[split]:
            labels = row["labels"]
            for i in labels:
                raw_label_counts[names[i]] += 1

            text = clean_text(row["text"])
            if not text:
                removed["empty_text"] += 1
                continue
            if text.lower() in _PLACEHOLDERS:
                removed["deleted_placeholder"] += 1
                continue
            text, redactions = USERNAME_RE.subn("[user]", text)

            label, reason = resolve_tom_label(labels, names)
            if label is None:
                removed[reason] += 1
                continue

            if text in seen[split]:
                removed["duplicate_within_split"] += 1
                continue
            if text in seen_earlier:
                removed["cross_split_leakage"] += 1
                continue

            seen[split].add(text)
            kept.append({"text": text, "label": label, "source": SOURCE_NAME})
            if redactions:
                redacted_rows += 1  # rows IN THE OUTPUT containing [user]
            if any(GOEMOTIONS_TO_TOM[names[i]] is None for i in labels):
                kept_with_ignored_label += 1  # one source label silently dropped

        seen_earlier |= seen[split]
        kept_counts[split] = Counter(r["label"] for r in kept)
        total_kept += len(kept)

        # newline="\n" keeps output byte-identical across platforms
        with open(out_dir / f"{split}.jsonl", "w", encoding="utf-8", newline="\n") as fh:
            for record in kept:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    stats = {
        "raw_rows": {s: len(ds[s]) for s in SPLITS},
        "kept_rows": {s: sum(kept_counts[s].values()) for s in SPLITS},
        "total_kept": total_kept,
        "removed": dict(removed),
        "removed_total": sum(removed.values()),
        "username_redacted_rows": redacted_rows,
        "kept_with_ignored_label": kept_with_ignored_label,
        "out_dir": str(out_dir),
        "raw_label_counts": dict(raw_label_counts.most_common()),
        "tom_label_counts": dict(
            Counter({k: sum(kept_counts[s][k] for s in SPLITS) for k in EMOTION_LABELS}).most_common()
        ),
        "per_split_tom_counts": {s: dict(kept_counts[s].most_common()) for s in SPLITS},
        "labels_without_source": [
            k for k in EMOTION_LABELS if k not in {c for s in SPLITS for c in kept_counts[s]}
        ],
    }
    return stats


def print_stats(stats: dict) -> None:
    print("=== GoEmotions -> TOM preparation stats ===")
    print("raw rows:     ", stats["raw_rows"], "total", sum(stats["raw_rows"].values()))
    print("kept rows:    ", stats["kept_rows"], "total", stats["total_kept"])
    print("removed total:", stats["removed_total"])
    for reason, n in sorted(stats["removed"].items(), key=lambda kv: -kv[1]):
        print(f"  {reason:<26} {n}")
    print(
        f"  kept w/ ignored label      {stats['kept_with_ignored_label']}"
        "  (>=1 source label dropped)"
    )
    print(f"  username rows redacted     {stats['username_redacted_rows']} (in output)")
    print("\nBEFORE — raw GoEmotions label distribution (label occurrences):")
    print(" ", stats["raw_label_counts"])
    print("\nAFTER — TOM label distribution (processed, all splits):")
    for label, n in stats["tom_label_counts"].items():
        if n:
            print(f"  {label:<12} {n}")
    if stats["labels_without_source"]:
        print(
            "no GoEmotions source for TOM labels:",
            ", ".join(stats["labels_without_source"]),
        )
    print("\nper-split processed counts:")
    for split, counts in stats["per_split_tom_counts"].items():
        print(f"  {split:<11} {sum(counts.values())} rows -> {counts}")
    print(f"\nwrote {{train,validation,test}}.jsonl -> {stats['out_dir']}")


def main() -> None:
    stats = prepare()
    print_stats(stats)
    # Non-zero exit if the pipeline silently produced nothing usable.
    if stats["total_kept"] == 0:
        sys.exit("ERROR: no rows survived processing")


if __name__ == "__main__":
    main()
