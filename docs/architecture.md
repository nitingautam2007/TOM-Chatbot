# TOM — Architecture

## Design goals

1. **Local-first, privacy-first** — no external AI APIs, no API keys, no data
   leaves the machine (except what the user explicitly chooses later).
2. **Replaceable intelligence** — chat replies come from `ChatService` →
   `ResponseSelector`. Every NLP/ML capability plugs in behind those service
   boundaries without touching routes or UI.
3. **Layered data access** — routes never run queries; only repositories touch
   SQLAlchemy; services orchestrate; repositories own SQL.
4. **Lightweight** — must run well on an i3-1005G1 with 8 GB RAM and no dGPU.
5. **Explainable, non-diagnostic NLP** — intent/emotion labels describe
   message content / expressed affect only; scores are similarity-derived,
   never presented as clinical probabilities.
6. **Safety before generation** — crisis-language screening runs on every
   chat message before the normal reply; risk labels are rule-based triage
   heuristics, never clinical assessments (Phase 4).

---

## Current architecture (Phase 1 + 2 + 3A + 3B + 4 + 5 + 6 — implemented)

```
┌──────────────────────────────┐          ┌───────────────────────────────────────────┐
│  Frontend (React + Vite)     │          │  Backend (FastAPI)                        │
│                              │  Axios   │                                           │
│  pages/Home, Chat, Dashboard │ ───────► │  api/routes/  (thin handlers only)        │
│        │ composes            │  CORS    │   health · chat · conversations · nlp      │
│  Screening page              │  :5173 → │   safety · screening                      │
│        ▼                     │  :8000    │        │ Pydantic validation              │
│  components/                 │ ◄─────── │        ▼ Depends(get_*_service)          │
│   layout/ common/ chat/      │  JSON    │  services/                                │
│        │                     │          │   ChatService · ConversationService       │
│  services/api.js  (all HTTP) │          │   NLPService (Phase 3A + 3B)            │
│  hooks/useChat.js            │          │   SafetyService (Phase 4)               │
│                              │          │   ScreeningService (Phase 5 PHQ-9)      │
│                              │          │   ResponseSelector (Phase 6+8 local replies)│
│                              │          │        │ only layer that builds SQL       │
│                              │          │        ▼                                  │
│                              │          │  services/nlp/                            │
│                              │          │   normalizer · language · embeddings      │
│                              │          │   intent · emotion · prototypes · scoring │
│                              │          │   data/ (prototype examples, en/hi/hing)  │
│                              │          │   (CPU-only multilingual MiniLM)          │
│                              │          │  services/safety/                         │
│                              │          │   patterns · context · scoring · detector │
│                              │          │   responses (ephemeral, no DB)            │
│                              │          │  services/phq9.py (pure scoring, no ML)   │
│                              │          │        │                                  │
│                              │          │        ▼                                  │
│                              │          │  repositories/                            │
│                              │          │   User · Conversation · Message           │
│                              │          │   Mood · Screening (PHQ-9 sessions)       │
│                              │          │        │                                  │
│                              │          │        ▼ SQLAlchemy 2 (async)              │
│                              │          │  database/connection.py                    │
│                              │          │   engine + sessionmaker + get_session      │
│                              │          │        │                                  │
│                              │          │        ▼ asyncpg                          │
│                              │          │  PostgreSQL 18 · tom_chatbot               │
│                              │          │  (schema managed by Alembic)               │
└──────────────────────────────┘          └───────────────────────────────────────────┘
```

### Key boundaries

- **UI never talks HTTP directly.** Every request goes through
  `frontend/src/services/api.js` — base URL, errors, conversation_id handling
  live in one place. The NLP endpoint is **not** wired into the UI yet
  (development/testing only).
- **Routes never contain business logic or SQL.** They validate with Pydantic,
  call a service via `Depends`, map domain errors to HTTP (e.g. 404, 422, 503).
- **Services own use-cases** (persist message → generate reply → persist reply
  → commit). They are the only callers of repositories.
- **Repositories own queries.** Swapping PostgreSQL later (or adding read
  replicas) never leaks into routes.
- **Reply generation stays AI-API-free** — `ResponseSelector` is pure local
  Python over the curated library; NLP/embeddings are optional and failures
  fall back without breaking chat.
- **NLP does not touch PostgreSQL.** Embeddings and NLP results are in-memory
  only (Phase 3A).

### Chat request flow (POST /api/chat)

1. React `ChatInput` → `services/api.js` → `POST /api/chat`
   (`{ message, conversation_id? }`)
2. Route parses `ChatRequest` (Pydantic) → 422 on invalid input
3. `ChatService.send_message`:
   - get/create the anonymous dev `User` (no personal data)
   - resolve `conversation_id` (404 if unknown) or create a new `Conversation`
   - save the **user** `Message`
   - **Phase 4:** run ephemeral `SafetyService.detect(message)` — if
     `requires_safety_response` (`high` / `imminent`), the reply is the
     non-clinical crisis redirect (**never** reaches Phase 6 generation)
    - **Phase 6/8 (normal path):** `NLPService.classify` (intent + emotion;
      failures swallowed → language-only fallback) + last
      `response_context_window` messages → `resolve_strategy` (Phase 8:
      greeting/farewell → positive/mixed → aligned intent → fallback) →
      `ResponseSelector.generate` (strategy bucket → lazy MiniLM semantic →
      fallback; deterministic context-aware variant rotation; en / hi / hinglish)
   - save the **assistant** `Message`
   - commit the transaction
4. Response: `{ conversation_id, message, response, is_safety,
   suggest_exercise }` — no internal scores, embeddings, or selection
   metadata
5. UI appends the reply; `conversation_id` is kept in `sessionStorage` so a
   page refresh restores history via `GET /api/conversations/{id}/messages`

### Persistence model (Phase 2)

| Table | Purpose |
| ----- | ------- |
| `users` | anonymous dev user (`id`, timestamps only — no PII) |
| `conversations` | thread per chat session (`user_id` FK, `title`) |
| `messages` | `role ∈ {user, assistant, system}`, `content`, ordered by `created_at` |
| `mood_checkins` | mood / stress / sleep / energy rows (later tracking phase) |
| `screening_sessions` | one screening run (`screening_type`, `score`, `severity`, `status`, `completed_at`) |
| `screening_responses` | per-question answers (unique per session + question) |

Conventions: **UUID** primary keys, **UTC** tz-aware timestamps, FKs with
`ON DELETE CASCADE`, indexes on all FKs + `(conversation_id, created_at)` for
message timelines.

Connection settings come **only** from `backend/.env`
(`TOM_DATABASE_URL`) — never from source, git, logs, or the React bundle.

---

## Phase 3A — NLP foundation (implemented)

**Purpose:** create the local NLP infrastructure that future intent, emotion,
safety, and screening models will use. This phase is **not** the final
chatbot intelligence and performs **no medical interpretation**.

```
raw text
  │
  ▼ validate (Pydantic + service)
normalize_text()          ← whitespace, Unicode, keep negation/punctuation
  │
  ▼
detect_language()         ← en | hi | hinglish | unknown
  │
  ▼
EmbeddingService.encode() ← paraphrase-multilingual-MiniLM-L12-v2 (CPU, 384-d)
  │
  ▼
NLPResult                 ← language, texts, embedding_dimension, processing_time_ms
```

### Module layout (`backend/app/services/nlp/`)

| File | Responsibility |
| ---- | -------------- |
| `types.py` | `LanguageCode`, `NLPResult`, `IntentResult`, `EmotionResult`, `ClassificationResult` |
| `normalizer.py` | Safe normalization — no stopword removal, preserves negation & Devanagari |
| `language.py` | Script analysis + distinctive-token Hinglish heuristic + langdetect fallback |
| `embeddings.py` | Lazy singleton `EmbeddingService`, CPU-only, `encode` / `encode_batch` |
| `service.py` | `NLPService.process()` / `NLPService.classify()` + FastAPI singleton |
| `intent.py` | Prototype intent classifier → label \| `unknown` |
| `emotion.py` | Prototype emotion classifier → label \| `uncertain` (+ negation damping) |
| `prototypes.py` | Cached class-centroid embeddings + cosine scoring (`PrototypeBank`) |
| `negation.py` | Lightweight negation cues / score damping |
| `scoring.py` | Thresholds, ambiguity margin, low-content fillers (`okay`/`hmm`/…) |
| `classifiers.py` | Public Phase 3B classifier surface |
| `data/intent_examples.py` | Curated intent prototypes (en/hi/hinglish) — not clinical data |
| `data/emotion_examples.py` | Curated emotion prototypes (en/hi/hinglish) — not clinical data |

### Supported languages

| Label | Example |
| ----- | ------- |
| `en` | `I have been feeling lonely lately.` |
| `hi` | `मुझे आज बहुत अकेला महसूस हो रहा है।` |
| `hinglish` | `Mujhe aajkal bahut lonely feel hota hai.` |
| `unknown` | empty / whitespace-only / unidentifiable |

### Hinglish handling (limitations)

Hinglish is romanised Hindi mixed with English. Generic language ID libraries
(including langdetect) do **not** understand it reliably. TOM classifies
Hinglish as an **application-level** decision:

1. ≥2 distinctive romanised-Hindi tokens → `hinglish` (or 1 token in a very
   short utterance)
2. langdetect says `hi` but script is Latin → `hinglish`
3. Otherwise fall back to langdetect / English-heuristic

This is transparent and testable but **imperfect** — short or unusual code-mix
can be mislabeled. A dedicated Hinglish classifier is out of Phase 3A scope.

### Embedding model

| Property | Value |
| -------- | ----- |
| Name | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Purpose | Multilingual sentence embeddings (semantic similarity) |
| Device | **CPU only** (`device="cpu"`, never GPU) |
| Dimension | **384** (read from the model at load time) |
| Load strategy | Lazy singleton — first `process()` loads; subsequent calls reuse |
| Cache | Hugging Face Hub cache under `~/.cache/huggingface/hub/` (not in git) |
| API exposure | Dimension only — **vector never returned** |

First model load is slower (weights from local cache); warm encode is typically
well under a second on this CPU. No CUDA / tensorflow packages are installed.

### Development endpoint

`POST /api/nlp/analyze` (OpenAPI tag `nlp-dev`):

- 200 → `NLPAnalyzeResponse` (language, original/normalized text, dimension,
  `processing_time_ms` from `time.perf_counter()`)
- 422 → empty / whitespace-only / missing field
- 503 → embedding model unavailable (controlled; chat still works)

Not stored in PostgreSQL. Not shown in the user-facing UI.

### Pipeline boundary (as implemented)

```
ChatService.send_message
    ↓
SafetyService (Phase 4 ✅) — crisis screen first; HIGH/IMMINENT → crisis reply, stop
    ↓ normal path
NLPService → intent + emotion classifiers (Phase 3B ✅ — prototype centroids)
    ↓
ResponseSelector (Phase 6 ✅) + resolve_strategy (Phase 8 ✅) — strategy bucket → semantic MiniLM → fallback
    ↓
optional later stages: symptom extraction, small local LLM (not implemented)
```

PHQ-9 screening (Phase 5 ✅) is a separate structured workflow — never
free-form reply generation. None of these stages diagnose conditions.

---

## Phase 3B — Intent + emotion classification (implemented)

**Purpose:** local prototype classifiers that label **message content**
(intent) and **expressed affect** (emotion). **Not psychiatric diagnoses.**

```
raw message
  │
  ▼
NLPService._analyze()     ← normalize · language · embed (Phase 3A)
  │  embedding (384-d, internal)
  ▼
classify_intent_text()     ← low-content guard → prototype centroids → cosine
  │                          threshold + ambiguity margin → label | unknown
  ▼
classify_emotion()         ← same scoring + negation damping
  │                          → label | uncertain
  ▼
ClassificationResult       ← language, texts, intent, emotion, processing_time_ms
                             (embedding vector never returned)
```

### Taxonomies

| Intent (15) | Emotion (10) |
| ----------- | ------------ |
| `greeting`, `goodbye`, `general_conversation`, `emotional_support`, `stress`, `anxiety`, `sadness`, `loneliness`, `academic_pressure`, `relationship_issue`, `sleep_concern`, `self_confidence`, `coping_help`, `help_seeking`, **`unknown`** | `sadness`, `anxiety`, `anger`, `stress`, `loneliness`, `happiness`, `positive`, `neutral`, `mixed`, **`uncertain`** |

### Scoring method (prototype centroids)

1. Curated examples live in `services/nlp/data/intent_examples.py` and
   `emotion_examples.py` (English / Hindi / Hinglish) — **not** a clinical
   dataset, **not** a downloaded corpus.
2. On first classify, each class’s example embeddings are averaged into a
   **centroid** and L2-normalized; cached in `prototypes.PrototypeBank`.
3. Query cosine vs each centroid → per-class scores.
4. **Negation damping** (`negation.py`): if a negation cue co-occurs with an
   emotion keyword, that class score is multiplied by `0.55`.
5. **Low-content guard** (`scoring.py`): pure fillers (`okay`, `hmm`, `fine`,
   `yeah`, …) → `unknown` / `uncertain`.
6. **Threshold + ambiguity** (from `Settings`):
   - top score &lt; `intent_confidence_threshold` / `emotion_confidence_threshold`
     → `unknown` / `uncertain`
   - (top − runner-up) &lt; `classification_ambiguity_margin` → `unknown` /
     `uncertain`

Configurable via env (`TOM_` prefix): `TOM_INTENT_CONFIDENCE_THRESHOLD`,
`TOM_EMOTION_CONFIDENCE_THRESHOLD`, `TOM_CLASSIFICATION_AMBIGUITY_MARGIN`.

**`confidence_score` is a cosine similarity (internal estimate), NOT a
calibrated probability and NOT clinically validated.**

### Development endpoint

`POST /api/nlp/classify` (OpenAPI tag `nlp-dev`):

- 200 → `{ original_text, normalized_text, language, intent, emotion,
  processing_time_ms }` with `intent`/`emotion` =
  `{ label, confidence_score, alternatives[{label,score}] }`
- 422 → empty / whitespace-only / missing field
- 503 → classifier / model unavailable (chat still works)

No embedding vector, no prototype vectors, no model internals in the response.

### Explicit non-goals (Phase 3B)

- Phase 3B itself adds no PHQ-9, no symptom extraction, no reply generation,
  and no safety rules — those shipped as separate later phases (4/5/6)
- No external AI APIs; no new heavy dependencies (uses Phase 3A stack only)
- Classification is a separate dev endpoint; chat safety routing lives in
  `ChatService` (Phase 4)

---

## Phase 4 — Safety / crisis-language detection (implemented)

**Purpose:** deterministic, local **crisis-language screening** that runs on
every chat message before the normal reply path, plus a development API for
manual testing. **Not a clinical assessment, diagnosis, risk score, or
emergency service.**

```
raw message
  │
  ▼ validate (Pydantic)
normalize_text()                 ← reuse Phase 3A normalizer
  │
  ▼
detect_language()                ← en | hi | hinglish | unknown
  │
  ▼
pattern match (patterns.py)      ← phrase/regex inventory per language
  │                                 (suicide ideation, self-harm, intent,
  │                                  plan, imminent, death wish, protective)
  ▼
context flags (context.py)       ← negation · protective · third-person
  │                                 hypothetical · quoted · past reference
  ▼
score_safety()                   ← max(base risk) + context caps
  │                                 + protective pull-down
  ▼
SafetyResult                     ← risk_level · requires_safety_response
                                    language · processing_time_ms
                                    signal_categories  (+ internal matches/score)
```

### Module layout (`backend/app/services/safety/`)

| File | Responsibility |
| ---- | -------------- |
| `types.py` | `RiskLevel`, `SignalCategory`, `SafetyMatch`, `SafetyContextFlags`, `SafetyResult` |
| `patterns.py` | Phrase/regex inventory (en / hi / hinglish) with base risk per pattern |
| `context.py` | Negation, protective, person, hypothetical, quoted, past detection |
| `scoring.py` | Aggregate matches + context → risk level + public categories |
| `detector.py` | Match patterns against normalized/searchable text |
| `responses.py` | Non-clinical crisis reply copy (uses configured resources only) |
| `service.py` | `SafetyService.detect()` / `response_for()` + FastAPI singleton |
| `__init__.py` | Public surface re-exports |

### Risk levels

| Level | Meaning (heuristic) | `requires_safety_response` |
| ----- | ------------------- | -------------------------- |
| `none` | No crisis-language signal | `false` |
| `low` | Topic-only / passive / heavily mitigated | `false` |
| `moderate` | Active ideation or self-harm language without clear intent/plan | `false` |
| `high` | Clear suicidal intent or plan (first-person, present) | `true` |
| `imminent` | Present-tense / method-now language | `true` |

### Signal categories (public)

`suicide_ideation`, `self_harm`, `death_wish`, `suicide_intent`,
`suicide_plan`, `imminent_danger`, `self_harm_intent`, `protective_context`,
`negation`, `ambiguous`.

These are **coarse tags for debugging/UI**, not clinical categories.

### Context handling

Phrasing context is considered before a risk level is assigned: negation,
protective language, third-person references, hypothetical framing, quoted or
reported speech, and past-tense references all down-weight or cap risk so a
mitigated or non-first-person mention is not scored like a present statement.
The exact rules and caps live in `backend/app/services/safety/` and are
intentionally not documented here.

Context rules are **heuristic, not a full dependency parser** — paraphrases
and novel phrasing outside the pattern set will be missed.

### Public API

`POST /api/safety/detect` (tag `safety`):

- **Request:** `{ "message": str (1–4000), "language"?: "en"|"hi"|"hinglish" }`
- **200:** `{ risk_level, requires_safety_response, language, processing_time_ms, signal_categories }`
- **422:** empty / whitespace-only / missing field
- **Never returned:** internal scores, weights, pattern IDs, regexes,
  matched spans, embedding vectors, or raw normalized text from this endpoint
- **Never logged:** the raw user message during safety detection

### Chat safety routing

`ChatService.send_message`:

1. Persist user message (unchanged)
2. `SafetyService.detect(message)` (ephemeral — **no DB row**; failures are
   logged and chat continues without a safety screen)
3. If `requires_safety_response` → reply = crisis redirect
   (`responses.crisis_response`) — **bypasses ResponseSelector**
4. Else → reply = `ResponseSelector.generate(...)` via `_normal_reply`
   (NLP classify + recent context; fallback copy on selector errors)
5. Persist assistant message + commit (unchanged)

Normal greetings, NLP endpoints (`/api/nlp/analyze`, `/api/nlp/classify`),
conversation APIs, and persistence behavior are unchanged.

### Configurable crisis resources

In `backend/.env` (never hardcoded, never invented):

```
TOM_SAFETY_EMERGENCY_NUMBER=
TOM_SAFETY_CRISIS_RESOURCE_URL=
```

When empty, crisis copy uses only generic “contact local emergency services /
a trusted person” guidance. Operators must fill in **local** numbers/links
before production use.

### Explicit non-goals / limitations (Phase 4)

- **Not clinical:** risk levels are not validated against any cohort, are not
  probabilities, and must not be used as professional triage.
- **Not exhaustive:** keyword/regex rules miss paraphrases, slang, sarcasm,
  and language outside the curated en/hi/hinglish patterns.
- **Not a substitute for care:** TOM is not an emergency service; crisis
  replies only redirect to human help.
- **No ML model:** Phase 4 adds zero packages, zero embeddings in the safety
  path, CPU-only pure Python.
- **Phase 5 (PHQ-9) / Phase 6 response engine are separate** from Phase 4 —
  this phase only defines the crisis short-circuit invariant.

---

## How Phase 3B+ components plug in

The route, schemas and persistence stay stable. Capabilities plug in through
`ChatService` (safety + orchestration) and `ResponseSelector` (Phase 6):

```
ChatService.send_message
        │
        ├─► SafetyService.detect          Phase 4 ✅ — HIGH/IMMINENT → crisis reply, stop
        │
        ▼ normal path
  ┌──────────────────┐
  │ NLPService       │  normalize · language · embed · classify (3A/3B ✅)
  ├──────────────────┤  failures → language-only fallback (never blocks chat)
  │ Recent context   │  last TOM_RESPONSE_CONTEXT_WINDOW messages (default 8)
  ├──────────────────┤  Phase 6+8 ✅
  │ ResponseSelector │  resolve_strategy → bucket → semantic MiniLM → fallback
  │  library.py      │  curated en/hi/hinglish copy (no intent×emotion matrix)
  ├──────────────────┤  Phase 7 ⬜ mood tracking · Phase 8 ⬜ (optional)
  │ LocalLLM         │  small quantised model if ever needed — still local
  └──────────────────┘
        │
        ▼
   reply (str)  →  ChatService persists it as an assistant Message
```

PHQ-9 screening (Phase 5) stays a **separate** structured workflow under
`ScreeningService` — never free-form response generation.

### Stage contract

```python
class SafetyService:  # Phase 4 ✅
    def detect(self, message: str, language: str | None = None) -> SafetyResult: ...

class ResponseSelector:  # Phase 6 ✅ (+ Phase 8 strategy)
    def generate(self, context: ResponseContext) -> GeneratedResponse: ...

# Phase 8 — pure strategy arbitration (no I/O), called inside generate():
def resolve_strategy(context: ResponseContext) -> Strategy: ...
```

`GeneratedResponse` carries `text`, `source`, `language`, `is_safety`,
`strategy` — internal confidence stays in-process and is never returned by
the API; `strategy` only exists so `ChatService` can map it to the additive
`suggest_exercise` flag (Phase 10).

### Safety invariant

The **safety engine runs on every message, before any generation step**. If it
flags `high` / `imminent`, the response path short-circuits to a crisis-support
message plus configured local resource guidance. No later generation (or
future LLM) can bypass this check (routing lives in `ChatService`, before
`ResponseSelector`).

### Response selection hierarchy (Phase 6 + Phase 8 strategy)

1. Safety HIGH/IMMINENT (or moderate + self_harm) → Phase 4 crisis reply
   (ChatService short-circuit — never reaches strategy/selector)
2. **Phase 8 `resolve_strategy(context)`** (pure, deterministic) picks a
   conversational strategy:
   - farewell / greeting (duration phrases are not farewells)
   - mixed emotion → clarification
   - confident positive emotion (incl. negation / temporal “now” state) →
     `positive_affect` even if intent says sadness (Phase 8 bug fix)
   - aligned negative / topical intent → corresponding support strategy
   - weak both → fallback
3. Strategy maps to a **library bucket** (intent preferred when
   confidence-gated match exists; else emotion) + context-aware variant
   rotation (skip recent repeats; no RNG)
4. Semantic retrieval via existing MiniLM embeddings (lazy per-language
   index, cosine ≥ `response_semantic_threshold` default 0.42) **only** when
   strategy has no curated bucket **and** emotion is not confidently driving
   a different reply
5. Safe conversational fallback (still multilingual, never exposes errors)

Selection is **deterministic** given the same message + recent window (no RNG)
so tests stay stable; variation comes only from conversation context.

**Not “emotion always wins”:** Phase 7 emotion accuracy ≈ 0.43, so emotion
only overrides when confident and mismatched with a weaker intent.

### Screening & tracking (Phases 5–6)

**Phase 5 (implemented):** structured **PHQ-9 depressive-symptom screening**
via `ScreeningService` (`services/screening_service.py`) + pure scoring
(`services/phq9.py`). Explicit workflow only — never auto-triggered from chat
(emotion/intent labels never start a screening).

```
POST /api/screening/phq9/start
  → ScreeningRepository.create_session (status=in_progress)
  → question 1 (timeframe: "Over the last 2 weeks")

POST /api/screening/phq9/{id}/answer   { question_number, answer ∈ {0,1,2,3} }
  → strict sequential order, unique answers, 409 on duplicate/out-of-order/complete
  → ScreeningResponse row (never logged)

POST /api/screening/phq9/{id}/complete  (only when 9 answers present)
  → score = sum(answers)  (0–27, pure arithmetic — no ML/embeddings)
  → severity band (minimal → severe)
  → if item 9 > 0: SafetyService.detect(probe)  ← Phase 4 authoritative
       high/imminent → safety_response prioritized over severity summary
  → screening_sessions.status=completed, score, severity, completed_at
  → non-diagnostic disclaimer (screening ≠ diagnosis)
```

Endpoints: `start` · `answer` · `GET {id}` · `complete` under
`/api/screening/phq9`. Ownership uses the existing anonymous default user
(no auth yet) — foreign screenings return 404.

`MoodCheckin` exists; a later phase adds check-in APIs. The Dashboard shows
**real** conversation + PHQ-9 data (Phase 9); mood trends remain an honest
placeholder (no fake data).

---

## Phase 10 — guided stress relief (implemented)

**Purpose:** a small, fully offline **Stress Relief Exercises** feature plus
targeted code simplification. **No backend endpoint, no database table, no
ML, no media/dependency was added**, and the chat processing flow is
unchanged.

```
React UI → POST /api/chat → ChatService → SafetyService / NLP → ResponseSelector
                                                                   │
                                            (unchanged pipeline; one new output)
                                                                   ▼
ChatResponse { …, is_safety, suggest_exercise }  ← additive flag only
```

### Frontend structure

```text
frontend/src/
  data/exercises.js                 # content: 4 exercises, static data
  components/exercises/
    ExerciseCard.jsx                # list card (whole card is the button)
    ExercisePlayer.jsx              # timer + steps + Start/Pause/Next/Finish/Exit
    ExerciseFeedback.jsx            # "How do you feel now?" (Better / same / Worse)
  pages/Exercises.jsx               # list → player → feedback (local state only)
```

- **Exercises:** Breathing (Inhale → Hold → Exhale, 5 cycles ≈ 1 min, CSS
  orb + countdown), Grounding (5-4-3-2-1, manual Next), Muscle relaxation
  (hands → shoulders → face → legs, manual Next), Calm moment (3 timed
  steps).
- **Step model:** a step with `seconds` auto-advances while running; a step
  without it waits for **Next**. Pause freezes the countdown
  (`setInterval` cleared on pause/unmount). Progress bar +
  `role="progressbar"` + `role="status"` announcements.
- **Accessibility:** native buttons, focus parked on headings only when the
  previous view unmounted, `prefers-reduced-motion` disables the decorative
  orb (label + countdown always carry the state), no external media.

### Chat integration (one additive field)

1. `ResponseSelector.generate` returns the Phase 8 `strategy` it used on
   `GeneratedResponse.strategy` (internal — never serialized as-is).
2. `ChatService` maps it to `suggest_exercise: true` **only** for
   `stress_support` / `anxiety_support` / `coping_support` /
   `academic_support` (the `_EXERCISE_STRATEGIES` set).
3. The UI renders a "Try a quick exercise" button under that reply →
   `/exercises`.

### Safety relationship (non-negotiable)

- The safety branch in `ChatService.send_message` runs **before** the normal
  path and hard-codes `suggest_exercise = False`; `SafetyService`, its
  thresholds and the Phase 4/7/8 contract are **untouched**.
- The UI additionally refuses to render the exercise button on any message
  with `is_safety = true`.
- `backend/tests/test_phase10.py` pins the three required prompts
  (`is_safety=true`, `suggest_exercise=false`) and locks the strategy set.
- Exercises are never persisted and never replace a crisis reply.

### Limitations

- Exercises are plain relaxation practices — **not treatment, not a
  clinical intervention, no scoring or diagnosis**; post-exercise feedback is
  stored nowhere and interpreted nowhere.
- `suggest_exercise` is per-message (derived from one message's strategy),
  not a multi-turn stress detector, and is **ephemeral** — restored history
  does not re-offer it (deliberately no new DB column).
- Offline after load; no video, no streaming, no external APIs.

---

## Multilingual strategy

- Language detection runs first in the pipeline (English / Hindi / Hinglish) —
  **Phase 3A foundation is in place**.
- Hinglish is romanised Hindi + code-mixed English — models and lexicons are
  curated for all three; Phase 3A uses a heuristic, later phases may refine.
- **Phase 6 responses** are maintained per language in
  `services/response/library.py` (en / hi Devanagari / hinglish Roman).
  `unknown` language defaults to English.

---

## Security notes

- No secrets in source; `backend/.env` is git-ignored; `.env.example` holds
  only a placeholder password.
- Database URLs/passwords are never logged, raised, or returned by any API.
- CORS restricted to `http://localhost:5173` (configurable via settings).
- Phase 9: requests carrying a **foreign `Origin` are rejected with 403** —
  CORS headers alone never reject a request; the middleware does.
- Phase 9: NLP request bodies are bounded (1–4000 chars); unexpected
  exceptions return JSON `{"detail": "Internal server error"}` with CORS
  headers and never leak tracebacks or driver/credential detail (DB down →
  JSON 503).
- React only ever talks to FastAPI — DB credentials never reach the browser.
- Message contents are stored for the user's own conversations only; no
  third-party analytics or AI calls.
- No AI API keys exist anywhere in the project — by design, permanently.
- NLP: raw mental-health messages are not logged by the NLP layer; embeddings
  and prototype centroids are not logged, not exposed, and not persisted
  (Phases 3A/3B).
- Safety (Phase 4): raw/normalized messages are **not logged** during safety
  detection; matches, scores, and pattern IDs stay in-process and are never
  returned by the public API; safety results are never written to PostgreSQL.
- Screening (Phase 5): PHQ-9 questionnaire answers are stored only in
  PostgreSQL for the owning user and are **never logged** or sent off-box;
  no analytics/telemetry; item-9 safety routing reuses Phase 4 resources only.
- Auth is a later phase; the API currently uses a single **development-only
  anonymous user** (no login, no personal data — not production authentication).

---

## Operational

| Concern      | Choice |
| ------------ | ------ |
| Server       | Uvicorn (`app.main:app`), `--reload` in dev |
| Validation   | Pydantic v2 schemas in `schemas/` |
| DB driver    | asyncpg via async SQLAlchemy 2.x |
| Pooling      | `NullPool` (safe across uvicorn/test event loops) |
| Migrations   | Alembic (`0001_initial_schema.py`, `0002_screening_status.py`, `0003_message_safety_flag.py`) |
| CORS         | Explicit allow-list from `core/config.py` (+ Phase 9 foreign-Origin 403) |
| Config       | `core/config.py` reads `backend/.env` (`TOM_` prefix) |
| Tests        | `backend/tests/` (pytest) — API + DB + NLP + classification + safety + screening + Phase 9 reliability/security, self-cleaning |
| Frontend     | Axios instance in `services/api.js`; vitest + testing-library (`npm test`) |
| NLP model    | CPU-only sentence-transformers, lazy singleton (`services/nlp/`) |
| Classifiers  | Prototype centroids + cosine (`services/nlp/{intent,emotion}.py`) |
| Safety       | Rule-based patterns + context caps (`services/safety/`) |
| Screening    | PHQ-9 pure scoring + session workflow (`services/phq9.py`, `services/screening_service.py`) |
| Version      | `0.10.0-phase10` |
