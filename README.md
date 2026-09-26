# TOM — Mental Health Support Chatbot

> **A privacy-first, local-only mental-health support chatbot that speaks English, Hindi and Hinglish.**
> Built as a B.Tech AI & ML project — explainable NLP, safety-first design, and honest evaluation.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?logo=tailwindcss&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)
![NLP](https://img.shields.io/badge/NLP-100%25_local-2563EB)
![AI_APIs](https://img.shields.io/badge/AI_API_keys-none-green)
![Tests](https://img.shields.io/badge/tests-416_backend_%7C_22_frontend-blue)

**Version:** `0.10.0-phase10`

> ⚠️ **Not a medical device.** TOM is a *support* chatbot — not a doctor, not a
> therapist, **not a diagnostic system**. It must never be treated as clinical
> validation or a substitute for professional care.

---

## Overview

TOM listens, classifies what you say (intent + emotion), screens for crisis
language **before** anything else, and replies with supportive responses —
all on your own machine. No cloud LLM, no AI API keys, no message content
leaving the computer.

### Why TOM?

- **Privacy by architecture** — inference is local; the only network calls are
  between your browser and localhost.
- **Multilingual by design** — English, Devanagari Hindi, and Roman Hinglish
  (code-mixed) are first-class input languages.
- **Safety-first ordering** — the crisis screen runs *before* NLP or response
  selection, and wins over everything else.
- **Honest engineering** — weak metrics are published (emotion accuracy ≈ 0.43),
  placeholders say "not implemented yet" instead of showing fake data, and
  every claim in this README maps to code you can read.

---

## Features

### ✅ Implemented (works today)

| Feature | What it does |
|---|---|
| **Chat** | Local supportive replies, conversation persistence, history restored after refresh, multilingual input (EN/HI/Hinglish) |
| **Safety screening** | Rule-based crisis-language detection runs first; high risk short-circuits to a crisis response and is flagged `is_safety` |
| **Intent & emotion** | 15 intent labels + 10 emotion labels via prototype-centroid classifiers (explainable, threshold-gated) |
| **Response strategy** | Deterministic intent/emotion arbitration → curated response library (EN/HI/Hinglish) → semantic fallback |
| **PHQ-9 check-in** | Structured 9-question screening session, scoring 0–27, severity bands, item-9 routed through SafetyService |
| **Stress-relief exercises** | 4 offline exercises (breathing, grounding, muscle relaxation, calm) with timed/stepped player + chat suggestion button |
| **Dashboard** | Real conversation count + latest PHQ-9 result with honest empty states |
| **Evaluation harness** | Phase 7 (95 classification + 27 safety cases) and Phase 8 (99 strategy cases) runners with regression gates |

### 🚧 In development

- **Dataset pipeline for a trained classifier** — GoEmotions is downloaded,
  mapped to TOM labels, cleaned and split (see [Dataset](#-dataset-goemotions)).
  The model itself is **not trained yet**.

### 📋 Planned (not started)

- Train and compare **TF-IDF + Logistic Regression** vs **TF-IDF + Linear SVM**
  on the prepared dataset, evaluate, then integrate *only if* it beats the
  prototype classifiers
- Hindi/Hinglish labelled dataset (current data is English-only)
- Mood/stress/sleep tracking (Dashboard placeholder is explicit — no fake data)
- Authentication (currently a development-only anonymous user)

---

## Architecture

```mermaid
flowchart TD
    U["React frontend (Vite + Tailwind)"] -->|"POST /api/chat"| F["FastAPI"]
    F --> C["ChatService"]
    C --> S["SafetyService — rule-based, runs FIRST"]
    S -->|"high / imminent risk"| R1["Crisis response (is_safety=true)"]
    S -->|"normal"| N["NLPService<br/>normalize → language → embed → intent/emotion"]
    N --> P["ResponseSelector<br/>strategy → curated library → semantic fallback"]
    P --> R2["Local supportive reply"]
    C --> DB[("PostgreSQL<br/>conversations · messages · PHQ-9")]
```

**Layered backend:** `routes → services → repositories → SQLAlchemy → PostgreSQL`.
Routes never write queries; services never leak DB details to the API layer.

### How a message flows (plain version)

```text
User message
     ↓
Normalization            (whitespace/punctuation cleanup — keeps negations)
     ↓
Language detection       (en / hi / hinglish / unknown)
     ↓
Embedding                (multilingual MiniLM, 384-dim, CPU)
     ↓
Intent / Emotion         (cosine similarity vs curated prototypes)
     ↓
Safety analysis          ← runs FIRST in ChatService, before the steps above
     ↓                     on crisis: static crisis reply, NLP never runs
Response strategy        (deterministic intent/emotion arbitration)
     ↓
Response                 (curated EN/HI/Hinglish library or semantic match)
     ↓
PostgreSQL               (message + conversation persisted)
```

| Component | Role (viva one-liner) |
|---|---|
| **ChatService** | Orchestrates one message: persist → safety → NLP → strategy → reply → persist |
| **SafetyService** | Deterministic crisis-language triage; matches/scores never leave the service |
| **NLPService** | Normalization, language detection, embedding, intent/emotion classification |
| **ResponseSelector** | Picks reply strategy, then the best library entry (or semantic fallback) |
| **Repositories** | The only layer that touches the database |
| **PostgreSQL** | Conversations, messages, PHQ-9 sessions — via async SQLAlchemy + Alembic |

### Interactive diagrams (live)

Open in-browser with zoom/pan/theme controls via GitHub Pages — a plain GitHub
file link only shows HTML source:

[High-Level](https://nitingautam2007.github.io/TOM-Chatbot/tom-highlevel.architecture.html) ·
[Chat Flow](https://nitingautam2007.github.io/TOM-Chatbot/tom-chatflow.architecture.html) ·
[NLP](https://nitingautam2007.github.io/TOM-Chatbot/tom-nlp.architecture.html) ·
[Safety](https://nitingautam2007.github.io/TOM-Chatbot/tom-safety.architecture.html) ·
[PHQ-9](https://nitingautam2007.github.io/TOM-Chatbot/tom-phq9.architecture.html) ·
[Data Flow](https://nitingautam2007.github.io/TOM-Chatbot/tom-dataflow.architecture.html)

---

## 🤖 AI / ML

**Design rule: no external AI APIs — ever.** No OpenAI, Gemini, Claude, Grok,
or any cloud LLM. Enforced by `tests/test_eval_security.py`, which fails the
build if such an import appears.

### Current ML components (implemented)

| Component | Approach | Evidence |
|---|---|---|
| **Embeddings** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384-dim, CPU-only, lazy singleton | `backend/app/services/nlp/embeddings.py` |
| **Intent classifier** | 15 labels · curated prototype utterances → class centroids → cosine similarity → confidence threshold (0.40) + ambiguity margin → else `unknown` | `intent.py`, `prototypes.py`, `data/intent_examples.py` |
| **Emotion classifier** | 10 labels · same prototype-centroid method + negation damping → else `uncertain` | `emotion.py`, `data/emotion_examples.py` |
| **Safety detection** | Deterministic keyword/regex rules + context handling (negation, third-person, hypothetical, quoted, past). **No ML** | `services/safety/` |
| **Response strategy** | Deterministic intent/emotion arbitration (17 strategies), rule precedence — no model, no RNG | `response/strategy.py` |

Current evaluation (synthetic, engineering — **not clinical validation**):

| Gate | Result |
|---|---|
| Intent accuracy (n=95) | 0.674 |
| **Emotion accuracy (n=95)** | **0.432 ← weakest metric, honestly reported** |
| Language detection (n=95) | 0.958 |
| Safety contract (27 cases) | 27/27, 0 failures |
| Response strategy (99 cases) | accuracy 1.0, forbidden replies 0, gates ✅ |

### Planned model (NOT trained yet)

```text
TF-IDF + Logistic Regression   vs   TF-IDF + Linear SVM
        train on data/processed/go_emotions_tom
        → evaluate (per-class F1, class-weight=balanced)
        → integrate ONLY if it beats the prototype classifiers
```

Nothing in `models/` today — it is an intentionally empty placeholder.

---

## 📊 Dataset — GoEmotions

Prepared with a reproducible, auditable pipeline
(`backend/evaluation/data/prepare_go_emotions.py`) — **data preparation only,
no model trained yet.**

```text
Raw:      54,263 samples  (train 43,410 · validation 5,426 · test 5,427)
          28 original emotion labels, multi-label, English, CC-BY-4.0

Processed: 42,337 samples (train 33,934 · validation 4,209 · test 4,194)
           fields: text · label · source   (no usernames, URLs, ids)
```

**Processing applied:** TOM label mapping (19 source labels mapped, 9 ignored
— never forced) · exact-duplicate removal (155) · **cross-split leakage
prevention (71)** · username/handle redaction · original split membership
preserved (never reshuffled).

**TOM emotion labels represented:**

```text
sadness   anxiety   anger   happiness   positive   neutral
```

**No direct GoEmotions source (deliberately not faked):**

```text
stress   loneliness   mixed   uncertain
```

Class imbalance is real: `neutral` 39% · `positive` 34% · `anxiety` only 753
rows. Full analysis (mapping rationale, quality audit, limitations):
[docs/dataset/go_emotions_analysis.md](docs/dataset/go_emotions_analysis.md).

---

## 🛡️ Safety & Privacy

TOM is a **support tool, not a medical diagnostic system.**

- **Safety runs first.** `ChatService` screens every message before NLP. On
  high/imminent risk the reply is a non-clinical crisis redirect; the normal
  reply path never runs.
- **Context-aware rules.** Negation, protective, third-person, hypothetical,
  quoted and past-tense phrasing down-weight risk, so "I don't want to…" is
  not scored like a first-person statement. Exact rule internals live in
  `backend/app/services/safety/` and are intentionally not documented here.
- **Pattern-based limits.** Rules match curated phrases — they miss paraphrases,
  sarcasm and novel phrasing. Risk labels are **triage heuristics, not clinical
  assessments**, and must never be treated as emergency triage.
- **PHQ-9 = screening, not diagnosis.** Standard 9-item instrument (0–27 +
  severity bands); every result carries a non-diagnostic disclaimer. Item 9
  routes through SafetyService. English questionnaire only.
- **Privacy.** No auth (dev-only anonymous user) · messages stored only in
  local PostgreSQL · safety matches never persisted or logged · `.env`
  git-ignored · processed dataset redacts identifiers · frontend stores only
  conversation/session IDs (never message or answer content).

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 · Vite 6 · Tailwind CSS v4 · React Router 6 · Axios · Lucide icons · Vitest |
| Backend | Python 3.12 · FastAPI · Uvicorn · Pydantic v2 |
| Database | PostgreSQL 18 · SQLAlchemy 2.x (async) · asyncpg · Alembic |
| NLP / ML | sentence-transformers (CPU) · langdetect · scikit-learn *(planned for trained classifier)* |
| Data | Hugging Face `datasets` *(data-prep only, see `requirements-data.txt`)* |

**Target hardware:** Intel Core i3-1005G1, 8 GB RAM, no GPU — inference is
CPU-only by design.

---

## 📁 Project Structure

```text
Tom Chatbot/
├── backend/
│   ├── app/
│   │   ├── api/               # routes: health, chat, conversations, nlp, safety, screening
│   │   ├── services/
│   │   │   ├── nlp/           # normalization, language, embeddings, intent, emotion (+ prototype data)
│   │   │   ├── safety/        # rule-based crisis detection (runs first)
│   │   │   └── response/      # strategy arbitration + curated EN/HI/Hinglish library
│   │   ├── repositories/      # only layer that runs DB queries
│   │   ├── models/  schemas/  # SQLAlchemy entities · Pydantic contracts
│   │   └── database/  core/   # async engine/session · settings
│   ├── evaluation/            # synthetic datasets, run_phase7 / run_phase8, dataset prep
│   │   └── data/prepare_go_emotions.py
│   ├── alembic/               # 3 migrations (schema, screening, is_safety)
│   ├── tests/                 # 416 tests (API, DB, NLP, safety, screening, response, data)
│   └── requirements.txt · requirements-data.txt · .env.example · pytest.ini
│
├── frontend/
│   ├── src/
│   │   ├── components/        # common · layout · chat · exercises
│   │   ├── pages/             # Home · Chat · Screening · Exercises · Dashboard
│   │   ├── data/exercises.js  # static exercise content (offline)
│   │   ├── hooks/  services/  # useChat state · single Axios instance
│   │   └── test/              # 22 Vitest tests
│   └── package.json · vite.config.js · .env.example
│
├── data/
│   ├── raw/go_emotions/       # GoEmotions as downloaded (unaltered, CC-BY-4.0 + provenance README)
│   └── processed/go_emotions_tom/   # cleaned TOM-mapped JSONL (regenerable)
│
├── docs/
│   ├── architecture.md        # full architecture reference
│   ├── architecture/          # 7 interactive HTML diagrams (+ JSON sources)
│   ├── dataset/go_emotions_analysis.md
│   └── phase7|8_evaluation_metrics.json   # latest evaluation outputs
│
├── models/README.md           # placeholder — no model weights committed
├── scripts/archify.mjs        # diagram build wrapper
├── AGENTS.md                  # AI-assistant workflow rules for this repo
├── backend/README.md          # backend + full API reference
└── README.md                  # ← you are here
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12** and **Node.js 18+**
- **PostgreSQL 18** on `localhost:5432`, database `tom_chatbot`

### 1. Database & environment

```powershell
cd backend
Copy-Item .env.example .env
# edit backend/.env → set TOM_DATABASE_URL with YOUR password
```

```
TOM_DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/tom_chatbot
```

> `.env` is git-ignored. Never commit, print, or share the password.
> Optional: `TOM_SAFETY_EMERGENCY_NUMBER`, `TOM_SAFETY_CRISIS_RESOURCE_URL`
> for your local crisis resources (no numbers/URLs are invented in code).

### 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head                 # create tables
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger): <http://localhost:8000/docs>

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

The two apps run independently; CORS allows `http://localhost:5173`.
Database credentials never reach React.

### NLP model download

The embedding model downloads automatically on first use from Hugging Face
(no API key, cached locally). Offline without a cache → `/api/nlp/analyze`
returns a controlled 503; `/api/chat` still works.

---

## 🛠️ Development

```powershell
# Backend
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev

# Migrations
alembic upgrade head · alembic current · alembic downgrade -1

# Regenerate the processed dataset from raw (reproducible)
cd backend
.venv\Scripts\python -m evaluation.data.prepare_go_emotions
```

### API endpoints (summary)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` · `/api/health` | Status, version, health |
| POST | `/api/chat` | Send message → local reply (+ `conversation_id`, `is_safety`, `suggest_exercise`) |
| GET/POST | `/api/conversations` · `/{id}` · `/{id}/messages` | Persistence & history |
| POST | `/api/nlp/analyze` · `/api/nlp/classify` | Dev-only NLP inspection (no vectors returned) |
| POST | `/api/safety/detect` | Rule-based crisis screening (not clinical) |
| POST/GET | `/api/screening/phq9/…` | PHQ-9 start → answer → get → complete |

Full reference: [backend/README.md](backend/README.md).

---

## 🧪 Testing & Evaluation

```powershell
# Backend tests (API, DB, NLP, safety, screening, response, dataset)
cd backend
.venv\Scripts\python -m pytest -q

# Frontend tests + production build
cd frontend
npm test
npm run build

# Regression evaluations (write docs/phase*_evaluation_metrics.json)
cd backend
.venv\Scripts\python -m evaluation.run_phase7
.venv\Scripts\python -m evaluation.run_phase8
```

**Current status (verified):** backend **416 passed** · frontend **22 passed** ·
build ✅ · Phase 7 gates ✅ (safety 27/27) · Phase 8 gates ✅ (strategy 1.0).

Notes: DB tests self-clean and skip with a hint if `backend/.env` is missing.
NLP tests load the embedding model once. Evaluation sets are synthetic
engineering aids — **not clinical validation**.

---

## ⚠️ Limitations

- **Not clinical.** No component diagnoses anything; PHQ-9 is screening only;
  risk labels are triage heuristics.
- **Prototype classifiers are small** (hand-curated examples); emotion accuracy
  ≈ 0.43 is the weakest metric — a trained classifier is the planned remedy.
- **Safety is pattern-based** — paraphrases, sarcasm and novel phrasing can be
  missed. It does not replace emergency services or professional care.
- **English-only data and PHQ-9 wording** (UI copy English; Hindi/Hinglish
  accepted as input, not translated).
- **No auth** — single development anonymous user; not production-hardened for
  multi-user deployment.
- **No mood/stress/sleep tracking yet** — the Dashboard says so explicitly
  rather than showing fabricated trends.

---

## 🗺️ Roadmap

```text
[x] React + FastAPI foundation                    (Phase 1)
[x] PostgreSQL persistence + repositories         (Phase 2)
[x] NLP pipeline: normalize · language · embed    (Phase 3A)
[x] Intent + emotion prototype classifiers        (Phase 3B)
[x] Rule-based safety engine                      (Phase 4)
[x] PHQ-9 structured screening                    (Phase 5)
[x] Local response library + selection            (Phase 6)
[x] End-to-end evaluation harness                 (Phase 7)
[x] Deterministic response-strategy layer         (Phase 8)
[x] Production hardening · a11y · frontend tests  (Phase 9)
[x] Stress-relief exercises + code cleanup        (Phase 10)
[x] GoEmotions dataset preparation (42,337 rows, leakage-safe)
[ ] Train TOM classifier: TF-IDF + LogReg vs Linear SVM
[ ] Evaluate honestly → integrate only if it beats prototypes
[ ] Hindi/Hinglish labelled dataset
[ ] Mood/stress/sleep tracking (Dashboard)
[ ] Authentication
[ ] Final academic documentation
```

---

## 🎓 Academic Context — why this project?

TOM demonstrates end-to-end engineering of an AI/ML system, not just a model:

- **Text classification** — intent/emotion prototypes today; supervised
  TF-IDF + linear models next, behind the same interface
- **Dataset engineering** — provenance, licensing, label mapping, dedup,
  train/test-leakage prevention, privacy redaction, reproducible pipeline
- **Evaluation discipline** — published metrics incl. weak ones, regression
  gates that fail the build
- **Safety-oriented design** — deterministic crisis layer with priority over
  ML, pinned by tests
- **Production fundamentals** — FastAPI + async SQLAlchemy + Alembic +
  repositories, error contracts, REST API
- **Full-stack delivery** — React SPA, accessibility (ARIA, reduced motion,
  contrast), 438 combined tests, CI-style local gates

Built and explained for a B.Tech viva: every component is small, readable,
and justifiable — no black boxes, no unnecessary abstraction.

---

## 📚 Documentation

| Document | Contents |
|---|---|
| [backend/README.md](backend/README.md) | Backend setup, API reference, test inventory |
| [docs/architecture.md](docs/architecture.md) | Full architecture reference (phases 1–10) |
| [docs/architecture/README.md](docs/architecture/README.md) | 7 interactive HTML diagrams |
| [docs/dataset/go_emotions_analysis.md](docs/dataset/go_emotions_analysis.md) | Dataset mapping, quality audit, limitations |
| [data/README.md](data/README.md) | Data rules, provenance, regeneration |
| [frontend/README.md](frontend/README.md) | Frontend structure & commands |

---

## Disclaimer

TOM is an academic engineering project. It is **not** a medical device, not a
diagnosis tool, not a treatment, and not a substitute for qualified
professional care. If you are in crisis, contact your local emergency
services or a crisis helpline immediately.

*No external AI APIs or AI API keys are used anywhere in this project.*
