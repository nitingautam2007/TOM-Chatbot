# Backend API

FastAPI service for TOM (Phase 6 — local response generation on top of Phase 5
PHQ-9 screening, Phase 4 safety, Phase 3B classification, Phase 3A NLP, and
Phase 2 persistence).

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Database configuration — create .env from the template and set your URL.
# NEVER commit .env or put real credentials anywhere else.
Copy-Item .env.example .env
# edit .env → TOM_DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/tom_chatbot

alembic upgrade head
```

### Phase 3A dependencies (local NLP)

`requirements.txt` includes:

- `langdetect` — lightweight language ID (English / Hindi fallback)
- `sentence-transformers` — pulls CPU **torch** + transformers (no CUDA,
  no tensorflow) for the multilingual embedding model

Phase 3B adds **no new packages** — it reuses the Phase 3A embedding stack.

Model (downloaded once via Hugging Face Hub, no API key):
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` — **CPU only**,
dimension **384**. Cache: `%USERPROFILE%\.cache\huggingface\hub\`.

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Docs: <http://localhost:8000/docs>

## Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/` | Project name, status, version |
| GET | `/api/health` | Health check |
| POST | `/api/chat` | Persist message + **local** reply; `{ "message", "conversation_id"? }` → `{ conversation_id, message, response }`. Safety HIGH/IMMINENT short-circuits to Phase 4 crisis copy; otherwise Phase 6 curated selection (intent → emotion → semantic MiniLM → fallback). No external AI APIs. |
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/{id}` | Conversation detail (404) |
| GET | `/api/conversations/{id}/messages` | Messages (404) |
| POST | `/api/nlp/analyze` | **Dev/test** — NLP analysis; 422 empty, 503 model down; no embedding vector |
| POST | `/api/nlp/classify` | **Dev/test** — intent + emotion labels; 422 empty, 503 classifier down; no vector, not a diagnosis |
| POST | `/api/safety/detect` | **Screening** — crisis-language risk level; 422 empty/whitespace/missing; no scores/patterns leaked |
| POST | `/api/screening/phq9/start` | **Phase 5** — start PHQ-9 session; 409 if one already in progress |
| POST | `/api/screening/phq9/{id}/answer` | Submit answer `{ question_number, answer }`; answer ∈ {0,1,2,3}; 409 duplicate/out-of-order/completed |
| GET | `/api/screening/phq9/{id}` | Screening state; 404 if not found or not owned |
| POST | `/api/screening/phq9/{id}/complete` | Score (0–27) + severity band + disclaimer; 409 if incomplete; item 9 > 0 → SafetyService |

### NLP analyze (Phase 3A)

```json
POST /api/nlp/analyze
{ "text": "Mujhe aajkal bahut lonely feel hota hai" }

→ 200
{
  "language": "hinglish",
  "original_text": "…",
  "normalized_text": "…",
  "embedding_dimension": 384,
  "processing_time_ms": 156.2
}
```

Not a diagnostic endpoint. Embeddings stay internal.

### NLP classify (Phase 3B)

```json
POST /api/nlp/classify
{ "message": "I feel sad and lonely today" }

→ 200
{
  "original_text": "…",
  "normalized_text": "…",
  "language": "en",
  "intent":  { "label": "sadness", "confidence_score": 0.62, "alternatives": [ … ] },
  "emotion": { "label": "uncertain", "confidence_score": 0.64, "alternatives": [] },
  "processing_time_ms": 180.5
}
```

**Intent and emotion labels describe the content or expressed affect of a
message. They are not psychiatric diagnoses.** `confidence_score` is a
similarity-derived internal estimate — not a calibrated probability.

### Safety detect (Phase 4)

```json
POST /api/safety/detect
{ "message": "I will kill myself" }

→ 200
{
  "risk_level": "high",
  "requires_safety_response": true,
  "language": "en",
  "processing_time_ms": 2.1,
  "signal_categories": ["suicide_intent"]
}
```

**Risk levels are rule-based triage heuristics — not clinical assessments,
diagnoses, or predictions.** Internal scores, pattern IDs, regexes, and
matched text spans are never returned. 422 on empty / whitespace / missing
message. Set `TOM_SAFETY_EMERGENCY_NUMBER` and `TOM_SAFETY_CRISIS_RESOURCE_URL`
in `backend/.env` for local crisis resources (no numbers are hardcoded).

When chat detects `high` / `imminent`, `/api/chat` returns a non-clinical
crisis redirect instead of the normal local reply. Safety screening is
ephemeral (not stored in PostgreSQL).

## Architecture

```
route (api/) → service (services/) → repository (repositories/) → SQLAlchemy → PostgreSQL
                      │
                      ├─ services/nlp/  (Phase 3A+3B — no DB access)
                      │    normalizer → language → embeddings
                      │    → intent / emotion prototype classifiers → NLPService
                      │
                      └─ services/safety/ (Phase 4 — ephemeral, no DB)
                           patterns → context → scoring → SafetyService
```

- `api/routes/` — thin HTTP handlers (validation + delegation only)
- `api/deps.py` — service dependencies (`get_nlp_service`, chat, etc.)
- `schemas/` — Pydantic request/response models (`chat.py`, `conversation.py`, `nlp.py`)
- `services/chat_service.py` — chat persistence use-case (safety screen →
  normal reply via `ResponseSelector` or crisis redirect)
- `services/conversation_service.py` — conversation retrieval/creation
- `services/response/` — Phase 6 local reply selection (`ResponseSelector` +
  curated `library.py`, semantic MiniLM fallback, farewell-gated goodbye)
- `services/nlp/` — Phase 3A foundation + Phase 3B classifiers:
  - `normalizer.py` — safe text cleaning (keeps negation, Unicode, Hindi)
  - `language.py` — `en` / `hi` / `hinglish` / `unknown` detection
  - `embeddings.py` — lazy CPU singleton for multilingual MiniLM (384-d)
  - `service.py` — `NLPService.process()` + `NLPService.classify()`
  - `intent.py` / `emotion.py` — prototype centroid classifiers
  - `prototypes.py` — cached class-centroid embeddings + cosine scoring
  - `negation.py` — lightweight negation damping for emotion scores
  - `scoring.py` — thresholds, ambiguity margin, low-content fillers
  - `data/` — curated prototype examples (en/hi/hinglish), separate from code
  - `types.py` — `NLPResult`, `ClassificationResult`, `IntentResult`, …
- `services/safety/` — Phase 4 crisis-language detection (rule-based, no ML):
  - `types.py` — `RiskLevel`, `SignalCategory`, `SafetyResult`
  - `patterns.py` — phrase/regex inventory (en / hi / hinglish)
  - `context.py` — negation, protective, third-person, hypothetical, quoted, past
  - `scoring.py` — aggregate matches + context → risk level
  - `detector.py` — match patterns against normalized text
  - `responses.py` — non-clinical crisis reply copy (uses configured resources)
  - `service.py` — `SafetyService.detect()` + FastAPI singleton
- `services/phq9.py` — Phase 5 PHQ-9 constants + pure scoring (0–27, severity
  bands, English wording) — **no ML, no embeddings**
- `services/screening_service.py` — Phase 5 session workflow
  (start → answer ×9 → complete); item 9 > 0 routes through SafetyService;
  questionnaire answers never logged
- `api/routes/screening.py` — PHQ-9 endpoints under `/api/screening/phq9`
- `schemas/screening.py` — strict Pydantic validation (answer ∈ {0,1,2,3},
  question_number ∈ 1..9, strict ints — decimals/strings rejected with 422)
- `repositories/` — `user.py`, `conversation.py`, `message.py`, `mood.py`,
  `screening.py` — the only code that runs queries
- `models/` — `user.py`, `conversation.py`, `message.py`, `mood.py`,
  `screening.py` (UUID PKs, FK cascades, indexes, UTC times, `role` supports
  `user` / `assistant` / `system`; screening has `status` + `completed_at`)
- `database/connection.py` — async engine, sessionmaker, FastAPI `get_session`
  dependency
- `database/base.py`, `database/mixins.py` — declarative Base + UTC mixins
- `core/config.py` — settings from `backend/.env` (`TOM_` prefix), including
  `embedding_model_name` / `embedding_device=cpu`, Phase 3B thresholds
  (`intent_confidence_threshold`, `emotion_confidence_threshold`,
  `classification_ambiguity_margin`), Phase 4
  `safety_emergency_number` / `safety_crisis_resource_url`, Phase 6
  `response_context_window` / `response_semantic_threshold`, and version
  `0.6.1-phase6`

No AI API, no API keys. Credentials only via `.env` — never in source/logs.
The NLP layer does **not** diagnose mental-health conditions; intent/emotion
labels are content/affect annotations, not clinical findings. Safety risk
levels are **not** clinical assessments. PHQ-9 results are **screening
severity bands, not diagnoses**.

### Development-only anonymous user

There is **no authentication**. A single anonymous development user
(only `id` + timestamps, no personal information) is created on first use and
reused for all conversations. This is a development convenience, **not**
production authentication — a later phase will add real user accounts.

## Migrations

```powershell
alembic upgrade head      # apply all
alembic downgrade -1      # roll back one
alembic upgrade head      # re-apply
alembic current           # show revision
alembic revision --autogenerate -m "change"   # future changes
```

## Tests

```powershell
pytest    # 416 tests: Phases 1–10 — API, DB, NLP, classification, safety, screening, response, evaluation, reliability/security, exercise flag, dataset prep
```

- `tests/test_api.py` — Phase 1 endpoint contract: root, health, chat echo,
  chat reply, empty/missing validation (6 tests)
- `tests/test_database.py` — database configuration, connection, user /
  conversation / message creation, message persistence, conversation
  retrieval, message retrieval, invalid conversation ID, chat persistence,
  multiple messages in one conversation (11 tests)
- `tests/test_nlp.py` — normalization, language detection (en/hi/hinglish),
  embedding dimension/CPU/normalization, `NLPService`, `/api/nlp/analyze`
  (valid + 422 cases), chat independence (27 tests)
- `tests/test_classification.py` — intent (en/hi/hinglish), emotion (all 10
  labels + fallbacks), negation damping, low-content fillers, schemas,
  no-embedding-leak, `/api/nlp/classify` (valid + 422), chat independence,
  config/version (45 tests)
- `tests/test_safety.py` — risk levels (en/hi/hinglish), negation/context,
  API schema/no-leak, chat safety override, regression on normal chat and
  NLP endpoints (46 tests)
- `tests/test_screening.py` — PHQ-9 scoring/bands, schema validation
  (negative/decimal/string/missing/out-of-range), session lifecycle
  (start/duplicate/order/completion), persistence, ownership 404,
  item-9 SafetyService routing, log privacy, chat regression (49 tests)
- `tests/test_response.py` — Phase 6 curated library coverage, en/hi/hinglish
  selection, safety HIGH/IMMINENT bypass, context rotation, semantic/fallback,
  NLP failure, API contract, persistence (46 tests)
- `tests/test_response_quality.py` + `tests/test_eval_*.py` — Phase 7/8
  evaluation gates, response-strategy regression, performance/security
- `tests/test_phase9.py` — reliability/security contracts (503/500/403,
  bounded bodies, `is_safety` flag)
- `tests/test_phase10.py` — Phase 10 `suggest_exercise` flag: safety replies
  never suggest, stress replies do, mapping cannot widen
- `tests/test_data_prep.py` — GoEmotions pipeline invariants: raw exists,
  mapping covers all 28 labels, no empties/duplicates/leakage/usernames,
  output byte-reproducible

All DB tests self-clean: every row they create is deleted afterwards
(messages cascade with their conversation; screening sessions cascade their
responses). They never drop or truncate existing data, and DB tests skip
with a hint if `.env` is missing.
NLP / classification tests load the local embedding model once (CPU).
Safety tests use only the deterministic rule engine (no embeddings).
Screening tests use pure arithmetic scoring (no ML).
Response (Phase 6) tests are unit + API tests of local selection — no LLM.

**Classification, safety, screening, and response tests are engineering/dev
tests** — they assert behavior (labels, thresholds, schema shape, routing),
not clinical validity. PHQ-9 severity bands are not diagnoses. Response copy
is supportive only, never a diagnostic statement.
