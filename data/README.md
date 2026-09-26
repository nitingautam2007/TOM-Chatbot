# Data

Local datasets used for training and evaluating TOM's NLP/ML components.

## Contents

- `raw/go_emotions/` — GoEmotions (simplified) as downloaded from Hugging
  Face on 2026-09-26, **unaltered**. See `raw/go_emotions/README.md` for
  provenance, license (CC-BY-4.0) and verification notes.
- `processed/go_emotions_tom/` — cleaned, TOM-mapped, deduplicated
  JSONL (`train.jsonl` / `validation.jsonl` / `test.jsonl`; fields:
  `text`, `label`, `source`). Regenerate with:

  ```powershell
  cd backend
  .venv\Scripts\python -m evaluation.data.prepare_go_emotions
  ```

## Rules

- Never edit anything under `raw/` — it is the reproducible source of truth.
- Data-preparation dependencies live in `backend/requirements-data.txt`
  (NOT in `requirements.txt`, so production installs stay lean).
- All data must be free of personally identifiable information (PII).
  Preprocessing drops Reddit ids, placeholders and duplicate/leaky rows;
  no usernames or URLs are ever added.
