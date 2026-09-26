# GoEmotions (raw — do not alter)

## Dataset

- **Name:** GoEmotions, *simplified* configuration (the Hugging Face default)
- **Source:** `https://huggingface.co/datasets/google-research-datasets/go_emotions`
  (Demszky et al., Google Research — Reddit comments annotated for emotion)
- **Downloaded:** 2026-09-26, via `datasets.load_dataset` + `save_to_disk`
- **Loader version:** `datasets==4.8.5` (see `backend/requirements-data.txt`)
- **License:** CC-BY-4.0 (per the dataset card on Hugging Face)

## Reproduce the download (project root)

```python
from datasets import load_dataset
ds = load_dataset("google-research-datasets/go_emotions")   # config: simplified
ds.save_to_disk("data/raw/go_emotions")
```

## Original structure (as downloaded, unmodified)

| Split | Rows |
|---|---|
| train | 43,410 |
| validation | 5,426 |
| test | 5,427 |
| **total** | **54,263** |

- **Columns:** `text` (string), `labels` (list of class indices), `id`
  (Reddit submission id — metadata, **not** carried into processed data)
- **Labels:** 28 (27 fine-grained emotions + `neutral`), listed in
  `dataset_dict.json` / each split's `dataset_info.json`:
  admiration, amusement, anger, annoyance, approval, caring, confusion,
  curiosity, desire, disappointment, disapproval, disgust, embarrassment,
  excitement, fear, gratitude, grief, joy, love, nervousness, optimism,
  pride, realization, relief, remorse, sadness, surprise, neutral
- **Label cardinality:** multi-label — 45,446 rows have 1 label, 8,124 have
  2, 655 have 3, 37 have 4, 1 has 5

## Verification summary (2026-09-26)

- Missing/empty text: **0** in every split
- Exact duplicate rows (identical after whitespace normalization, beyond
  first): train 184 · validation 3 · test 6
- Cross-split identical texts: train∩validation 41 · train∩test 32 ·
  validation∩test 10 (handled by the preprocessing script, never by editing
  this raw copy)
- Language: English only (Reddit; ~14% of rows contain non-ASCII characters —
  emoji and punctuation, not other languages)
- User-identifying metadata: there are **no username/subreddit/score/timestamp
  columns** — only `text`, `labels`, `id` (a Reddit *submission* id, dropped
  during preprocessing). Note that, as free Reddit text, some rows *contain*
  third-party `u/…` handles (67 rows) and `r/…` subreddit refs (277 rows);
  there are no URLs or emails. Preprocessing **redacts all `u/…`/`@handle`
  identifiers to `[user]`** in the processed output; raw stays unaltered.
- Placeholder rows `[deleted]` / `[removed]` (exact match): counted during
  preprocessing — 0 found in this download (1 row *contains* the word
  `[deleted]` mid-sentence and is normal content)

## Important limitations

- Reddit-domain bias: informal, internet-culture language; not clinical text
- English only — no Hindi/Hinglish (TOM's other supported languages)
- Emotion *expression* labels, **not** mental-health diagnoses
- Multi-label annotation; only a subset of labels maps confidently to TOM
- Class imbalance (neutral ≈ 33% of rows)

## Preprocessing status

**Raw — unmodified.** Cleaning, TOM label mapping, deduplication and
split-leakage removal happen only in `data/processed/go_emotions_tom/`,
produced by `backend/evaluation/data/prepare_go_emotions.py`.
Never edit files in this directory.
