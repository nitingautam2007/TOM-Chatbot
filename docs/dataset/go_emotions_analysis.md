# GoEmotions → TOM Dataset Analysis

**Date:** 2026-09-26 · **Status:** data preparation only — no application code changed.
Companion documents: `data/raw/go_emotions/README.md` (provenance) ·
`backend/evaluation/data/prepare_go_emotions.py` (reproducible pipeline).

---

## Dataset

| Field | Value |
|---|---|
| Source | Hugging Face `google-research-datasets/go_emotions` (config: **simplified**) |
| Origin | Reddit comments annotated for emotion (Demszky et al., Google Research) |
| License | CC-BY-4.0 |
| Size | 54,263 rows (train 43,410 · validation 5,426 · test 5,427) |
| Columns (raw) | `text`, `labels` (multi-label indices), `id` (Reddit submission id) |
| Labels (raw) | 28: admiration, amusement, anger, annoyance, approval, caring, confusion, curiosity, desire, disappointment, disapproval, disgust, embarrassment, excitement, fear, gratitude, grief, joy, love, nervousness, optimism, pride, realization, relief, remorse, sadness, surprise, neutral |
| Cardinality | 45,446 rows have 1 label · 8,124 have 2 · 655 have 3 · 38 have 4+ |
| Language | English only |

---

## TOM compatibility

### TOM's existing emotion taxonomy (10 labels)

Owned by `backend/app/services/nlp/data/emotion_examples.py` — expresses
*felt affect*, never diagnosis:

`sadness` · `anxiety` · `anger` · `stress` · `loneliness` · `happiness` ·
`positive` · `neutral` · `mixed` · `uncertain`

### Full mapping table (28 → TOM)

Decision key: **MAP** = use as the listed TOM label · **IGNORE** = keep out of
the processed dataset (no confident TOM equivalent). No label is forced.

| GoEmotions label | → TOM emotion | Decision | Why |
|---|---|---|---|
| admiration | positive | **MAP** | Appreciation/warm evaluation; no admiration bucket in TOM |
| amusement | happiness | **MAP** | Laughter/play delight belongs to happiness |
| anger | anger | **MAP** | Direct, same construct |
| annoyance | anger | **MAP** | Mild irritation — anger's lower-intensity form; TOM has no separate bucket |
| approval | positive | **MAP** | Endorsement/support = warm positive affect (contrast `disapproval` below, which is rejection *of content*, not felt affect — annoyance would be the felt form and it already maps to anger) |
| caring | positive | **MAP** | Warm affiliation; nearest positive bucket (imperfect but positive-valence) |
| confusion | — | **IGNORE** | Cognitive state, not expressed affect |
| curiosity | — | **IGNORE** | Cognitive state, not expressed affect |
| desire | — | **IGNORE** | No TOM equivalent (craving, not a support-response trigger) |
| disappointment | sadness | **MAP** | Let-down affect; nearest TOM bucket. Distinct from neutral, so ignoring it would leak a sadness-family signal into neutral |
| disapproval | — | **IGNORE** | Evaluative stance toward content, not felt affect (unlike *annoyance*, which is felt) |
| disgust | — | **IGNORE** | Usually content-directed on Reddit; no TOM bucket, valence unclear |
| embarrassment | — | **IGNORE** | Self-conscious discomfort ≠ worry (anxiety) or low mood (sadness); forcing either would be wrong |
| excitement | happiness | **MAP** | High-arousal positive |
| fear | anxiety | **MAP** | Fear/worry is exactly what TOM's `anxiety` prototypes describe ("scared about the future") |
| gratitude | positive | **MAP** | TOM's own positive prototype is "I am grateful today" |
| grief | sadness | **MAP** | Bereavement/loss → sadness |
| joy | happiness | **MAP** | Direct, same construct |
| love | positive | **MAP** | Warm affection; no love bucket in TOM — positive is the warm-positive family |
| nervousness | anxiety | **MAP** | Direct (nervousness ≈ TOM anxiety prototypes) |
| optimism | positive | **MAP** | TOM positive prototype: "things are getting better" |
| pride | positive | **MAP** | Positive self-regard |
| realization | — | **IGNORE** | Cognitive insight, not affect |
| relief | positive | **MAP** | Resolved tension = positive valence |
| remorse | — | **IGNORE** | Guilt/self-blame; not sadness — no honest TOM equivalent |
| sadness | sadness | **MAP** | Direct, same construct |
| surprise | — | **IGNORE** | Valence-ambiguous (good or bad depending on context); forcing one side would inject label noise |
| neutral | neutral | **MAP** | Direct, same construct |

**Totals: 19 MAP · 9 IGNORE.**

TOM labels with **no GoEmotions source**: `stress`, `loneliness`, `mixed`,
`uncertain`.

- `stress` / `loneliness`: GoEmotions has no such labels — these must come
  from TOM's own prototypes or a future labelled source. They are **not**
  approximated by annoyance/nervousness (different constructs).
- `mixed`: a *structural* label (conflicting simultaneous feelings), which is
  exactly what GoEmotions' multi-label rows represent but never annotate as a
  single class — deliberately not faked here.
- `uncertain`: TOM's low-confidence fallback (no prototypes by design); never
  a training target.

### Multi-label rows (GoEmotions → single TOM label)

TOM's classifier is single-label, so per row:

1. Map every source label through the table.
2. All mapped labels agree on **one** TOM label → keep (e.g. `admiration +
   joy` → `positive`+`happiness` → conflict, but `joy + amusement` → `happiness`).
3. Nothing maps → drop (**unmapped**, 8,690 rows).
4. Mapped labels disagree → drop (**conflicting**, 3,010 rows).

A third, quieter category: rows mixing a mapped label with an IGNORED one
(e.g. `joy + confusion`) are **kept with the IGNORED signal dropped** —
2,942 rows (6.9% of kept). No label is invented for ambiguous rows; a future
revision may (a) map conflicting rows to TOM's `mixed`, or (b) add a
same-family tie-break (`happiness` beats `positive`) to recover ~958 rows
that currently conflict only within the positive family.

---

## Data quality

### Processed result (`data/processed/go_emotions_tom/`)

| | Rows |
|---|---|
| Raw | 54,263 |
| **Processed (kept)** | **42,337** (train 33,934 · validation 4,209 · test 4,194) |
| Removed | 11,926 (22.0%) |

| Removal reason | Rows |
|---|---|
| Unmapped (all source labels IGNORED) | 8,690 |
| Conflicting mapped labels | 3,010 |
| Exact duplicate within split (after cleaning) | 155 |
| Cross-split identical text (leakage guard) | 71 |
| Empty text | 0 |
| `[deleted]` / `[removed]` placeholders | 0 |

Additionally, identifiers are redacted in the pipeline: **63 processed rows**
contain `[user]` placeholders (`u/…`, `/u/…` any case, and `@handles`); a
final scan of all 42,337 rows found **0** remaining identifiers. **249
`r/…` references across 232 rows** were kept — subreddits are not personal
data. Raw contains **0 URLs**; processed contains **0 URLs**. The raw `id`
column (Reddit submission id) is dropped entirely.

### Class distribution (processed, all splits)

| TOM label | Rows | Share |
|---|---|---|
| neutral | 16,566 | 39.1% |
| positive | 14,450 | 34.1% |
| happiness | 4,210 | 9.9% |
| anger | 3,932 | 9.3% |
| sadness | 2,426 | 5.7% |
| anxiety | 753 | 1.8% |
| stress / loneliness / mixed / uncertain | 0 | — |

- **Severe imbalance:** `neutral` + `positive` = 73.3% of all rows;
  `anxiety` has only 753 rows (593 train / 77 validation / 83 test).
- **Suspicious content:** informal all-caps and profanity are normal Reddit
  register and were deliberately **not** removed (they carry emotion signal);
  text is truncated to ≤ 33 words by the source dataset itself.

### Privacy / metadata

- No usernames, submission ids, subreddit scores, timestamps or URLs in the
  processed files; fields are exactly `text`, `label`, `source`.
- All content is third-party public Reddit text under CC-BY-4.0 — no TOM user
  data is involved.

### Leakage

- Original split membership is **preserved** (never reshuffled).
- Identical cleaned text never appears in two splits: duplicates are dropped
  in split order (train → validation → test), removing 71 cross-split rows.

---

## Recommended training subset (for a future phase — not trained now)

- **Use:** all three processed splits as-is for a first TF-IDF + Logistic
  Regression / Linear SVM baseline over the **6 available labels**
  (`neutral`, `positive`, `happiness`, `anger`, `sadness`, `anxiety`).
- **Class imbalance:** the default for any TF-IDF + LogReg / Linear SVM
  baseline should be `class_weight="balanced"` with **macro-F1** as the
  selection metric and per-class F1 reported — not accuracy. Do not
  down-sample `neutral`/`positive` before a baseline has been measured.
  `anxiety` has only 77/83 rows in validation/test: treat its F1 as a wide
  confidence interval, not a tuning signal.
- **Do not train 10-class TOM emotion yet:** 4 TOM labels have zero source
  data here. A production-grade option (later phase, separate decision) is
  two-stage: GoEmotions pretrain → fine-tune on TOM's own labelled
  prototypes, or add a second source covering stress/loneliness.
- **Domain gap to measure:** GoEmotions ≠ supportive-chat register; evaluate
  on TOM's Phase 7 emotion set before believing any metric.

---

## Limitations

1. **Reddit-domain bias** — informal internet register, sarcasm, meme
   references; not the register of someone talking to a support chatbot.
2. **English only** — no Hindi/Hinglish, while TOM supports all three
   languages; this data cannot improve hi/hinglish emotion handling.
3. **Annotation limitations** — crowd-annotated single comments without
   conversation context; multi-label disagreements simplified by dropping
   3,010 conflicting rows rather than resolving them.
4. **Non-clinical** — labels describe expressed emotion in ordinary comments,
   not clinical states. No diagnostic value.
5. **Classification ≠ diagnosis** — a future model trained on this data
   predicts conversational affect for *response selection only*; it must
   never be presented as detecting depression, anxiety disorder or any
   condition, and must never gate SafetyService.
6. **Coverage gap** — 4 of 10 TOM labels (stress, loneliness, mixed,
   uncertain) have no usable source data here.
