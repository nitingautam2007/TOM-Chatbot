"""Phase 10 data-preparation tests (dataset task only — no chatbot behavior).

Guard the processed dataset's invariants: raw source exists, required fields,
no empty/duplicate rows, valid TOM labels, no split leakage, no usernames.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.nlp.data import EMOTION_LABELS
from evaluation.data import prepare_go_emotions as prep

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "go_emotions"
OUT_DIR = ROOT / "data" / "processed" / "go_emotions_tom"
SPLITS = ("train", "validation", "test")


@pytest.fixture(scope="module")
def raw_names() -> list[str]:
    datasets = pytest.importorskip(
        "datasets", reason="install backend/requirements-data.txt"
    )
    assert RAW_DIR.exists(), (
        f"Raw dataset missing: {RAW_DIR} — see data/raw/go_emotions/README.md"
    )
    ds = datasets.load_from_disk(str(RAW_DIR))
    return list(ds["train"].features["labels"].feature.names)


@pytest.fixture(scope="module")
def processed() -> dict[str, list[dict]]:
    assert OUT_DIR.exists(), (
        f"Processed dataset missing: {OUT_DIR} — run "
        "'.venv\\Scripts\\python -m evaluation.data.prepare_go_emotions'"
    )
    out: dict[str, list[dict]] = {}
    for split in SPLITS:
        path = OUT_DIR / f"{split}.jsonl"
        assert path.exists(), f"missing {path}"
        with open(path, encoding="utf-8") as fh:
            out[split] = [json.loads(line) for line in fh]
    return out


def test_raw_dataset_exists(raw_names: list[str]) -> None:
    assert (RAW_DIR / "dataset_dict.json").exists()
    assert len(raw_names) == 28


def test_mapping_covers_every_source_label(raw_names: list[str]) -> None:
    assert set(prep.GOEMOTIONS_TO_TOM) == set(raw_names)
    mapped = set(prep.GOEMOTIONS_TO_TOM.values()) - {None}
    assert mapped <= set(EMOTION_LABELS)


def test_resolve_tom_label_rules() -> None:
    names = ["joy", "sadness", "curiosity", "confusion", "desire"]
    assert prep.resolve_tom_label([0], names) == ("happiness", "ok")
    assert prep.resolve_tom_label([3, 4], names) == (None, "unmapped")
    assert prep.resolve_tom_label([0, 1], names) == (None, "conflicting")
    assert prep.resolve_tom_label([4, 0], names) == ("happiness", "ok")


def test_clean_text_is_conservative() -> None:
    assert prep.clean_text("  hello \n\t world  ") == "hello world"
    # keeps case, punctuation, emoji
    assert prep.clean_text("I am SO sad!! 😢") == "I am SO sad!! 😢"


def test_required_columns_and_source(processed: dict[str, list[dict]]) -> None:
    for split in SPLITS:
        assert processed[split], f"{split} is empty"
        for row in processed[split]:
            assert set(row) == {"text", "label", "source"}
            assert row["source"] == "go_emotions"


def test_no_empty_text(processed: dict[str, list[dict]]) -> None:
    for split in SPLITS:
        assert all(row["text"].strip() for row in processed[split])


def test_labels_are_valid_tom_labels(processed: dict[str, list[dict]]) -> None:
    valid = set(EMOTION_LABELS)
    for split in SPLITS:
        assert {row["label"] for row in processed[split]} <= valid


def test_no_duplicates_within_split(processed: dict[str, list[dict]]) -> None:
    for split in SPLITS:
        texts = [row["text"] for row in processed[split]]
        assert len(texts) == len(set(texts)), f"duplicate text within {split}"


def test_no_leakage_across_splits(processed: dict[str, list[dict]]) -> None:
    sets = {s: {row["text"] for row in processed[s]} for s in SPLITS}
    assert sets["train"] & sets["validation"] == set()
    assert sets["train"] & sets["test"] == set()
    assert sets["validation"] & sets["test"] == set()


def test_no_usernames_in_processed(processed: dict[str, list[dict]]) -> None:
    for split in SPLITS:
        assert not any(
            prep.USERNAME_RE.search(row["text"]) for row in processed[split]
        )


def test_output_is_reproducible(tmp_path: Path) -> None:
    """A fresh run from raw must recreate the committed processed files."""
    stats = prep.prepare(RAW_DIR, tmp_path)
    for split in SPLITS:
        assert (tmp_path / f"{split}.jsonl").read_bytes() == (
            OUT_DIR / f"{split}.jsonl"
        ).read_bytes(), f"{split}.jsonl differs from a fresh run"
    # accounting: every raw row is either kept or counted as removed
    assert sum(stats["raw_rows"].values()) - stats["removed_total"] == stats[
        "total_kept"
    ]
