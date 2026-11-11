# TOM Backend API Server

REST API for connecting the TOM frontend with the Python backend.

The backend keeps only short-lived, in-memory conversation context. It has no
user accounts, no durable chat database, and no consent records.

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the API server

```bash
python api_server.py
```

The server starts on **http://127.0.0.1:8000**.

---

## 🔌 API Endpoints

### `POST /api/chat`

Send a message and receive TOM's reply.

**Request:**

```json
{
  "message": "I am feeling sad today",
  "session_id": "anonymous-browser-session-id",
  "region": "IN"
}
```

All fields except `message` are optional:

- `message` must be a non-empty string of at most **2000 characters**.
- `session_id` must be a string of at most 128 characters. When omitted, the
  server creates one and stores it in the Flask session cookie for same-origin
  clients. The frontend always sends its own anonymous ID.
- `region` must be one of `IN`, `US_CA`, `UK`, or `INTL`. Invalid values fall
  back to `IN`.

**Response:**

```json
{
  "response": "I hear you. Would you like to tell me more about what's on your mind?",
  "intent": "sadness",
  "risk_level": "low",
  "resources": [],
  "region": "IN",
  "session_id": "anonymous-browser-session-id",
  "confidence": 0.6123,
  "source": "classifier"
}
```

`source` describes the path that produced the reply:

| Source | Meaning |
| --- | --- |
| `safety` | Deterministic crisis handling ran before every other path. |
| `quick_reply` | Exact match for a frontend mood or suggestion button. |
| `exact` | Exact match for a known training pattern (fast path). |
| `faq` | Question answered from the FAQ retrieval index. |
| `classifier` | TF-IDF + SVM intent classification. |
| `similarity` | Nearest-pattern support was stronger than the classifier. |
| `unknown` | TOM abstained instead of forcing a mental-health intent. |
| `validation` | The request was rejected before processing. |
| `rate_limit` | The per-session limit was reached. |
| `error` | An unexpected server error occurred. |

`risk_level` remains `"low"` or `"high"`. Crisis responses also include:

```json
{
  "intent": "crisis",
  "risk_level": "high",
  "risk_reasons": ["suicide"],
  "resources": [
    {
      "label": "Tele-MANAS",
      "description": "Free, 24/7 national mental health helpline.",
      "tel": "14416"
    }
  ],
  "region": "IN",
  "confidence": 1.0,
  "source": "safety"
}
```

#### Validation and error responses

| Status | `error` | When |
| --- | --- | --- |
| `400` | `invalid_request` | Missing/empty/non-string message, invalid session ID. |
| `404` | `not_found` | The endpoint does not exist. |
| `405` | `method_not_allowed` | Wrong HTTP method. The response includes an `Allow` header. |
| `413` | `message_too_long` | Message exceeds 2000 characters. |
| `413` | `request_too_large` | Request body exceeds 32 KB. |
| `429` | `rate_limited` | Per-session rate limit reached. Includes `retry_after` and a `Retry-After` header. |
| `500` | `server_error` | Unexpected server failure. Details stay in the server log. |

Example validation response:

```json
{
  "error": "invalid_request",
  "response": "Please send a message so I can respond.",
  "intent": "none",
  "risk_level": "low",
  "resources": [],
  "confidence": 0.0,
  "source": "validation"
}
```

#### Rate limiting

The default limit is **20 requests per 60 seconds per session**. State uses a
sliding window and is kept in memory only.

**Crisis messages bypass rate limiting entirely.** They are checked by the
deterministic safety layer before the limiter runs, so someone in danger is
never told to wait.

---

### `POST /api/session/reset`

Forget the short-lived context and rate-limit window for one session. The
frontend uses this when the user starts a new conversation.

**Request:**

```json
{
  "session_id": "anonymous-browser-session-id"
}
```

**Response:**

```json
{
  "status": "reset",
  "session_id": "anonymous-browser-session-id"
}
```

---

### `DELETE /api/data`

Delete the server-side data held for one browser session. TOM keeps no durable
chat records, so this clears the in-memory context and rate-limit state. The
frontend separately clears its local storage/session storage and consent
record.

**Request:**

```json
{
  "session_id": "anonymous-browser-session-id"
}
```

`session_id` may also be supplied as a query parameter.

**Response:**

```json
{
  "status": "deleted",
  "session_id": "anonymous-browser-session-id"
}
```

---

### `GET /api/health`

Liveness check with model, session, and runtime metrics. It returns `200` while
the process is running, even if the model is not ready.

**Response:**

```json
{
  "status": "online",
  "ready": true,
  "environment": "production",
  "version": "2.0.0",
  "model": "TOmChatbot (SVM)",
  "intents": 42,
  "patterns": 408,
  "faq_entries": 62,
  "sessions": 0,
  "messages": 0,
  "rate_limit_keys": 0,
  "uptime_seconds": 18.4,
  "timestamp": "2026-11-11T11:16:42Z",
  "message": "TOM backend is running and ready!"
}
```

### `GET /api/ready`

Readiness check for orchestrators. Returns `200` with `{"status": "ready",
"ready": true}` only when the classifier is loaded; otherwise returns `503` with
`{"status": "unavailable", "ready": false, "error": "model_unavailable"}`.

---

## 🔐 Request IDs and security headers

Every API response includes an `X-Request-ID` header. A safe client-supplied ID
of up to 64 characters (`A-Z`, `a-z`, `0-9`, `.`, `_`, `-`) is reused;
otherwise the server generates one. Use this ID when matching a user report to
server logs.

API responses also send:

- `Cache-Control: no-store`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`
- `Strict-Transport-Security` in production

Request logs are JSON objects containing metadata only (request ID, method,
path, status, duration, and remote address). Request logs never include message
content.

---

## 🎯 Supported Features

### Crisis handling

Crisis detection is deterministic and runs **before** quick replies, rate
limiting, FAQ retrieval, and the classifier. The classifier never trains on the
`crisis` or `suicide` labels, so ordinary phrases such as "I could die of
embarrassment" or "my mum died" are not misclassified as emergencies.

The frontend mirrors the same crisis resources and falls back to them when the
network is unavailable.

### Mood selection

The frontend sends mood messages in this format:

```text
"I'm feeling struggling today (😔)"
"I'm feeling low today (😕)"
"I'm feeling okay today (😐)"
"I'm feeling good today (🙂)"
"I'm feeling great today (😊)"
```

Both `"I'm feeling …"` and `"I am feeling …"` forms are accepted after
normalisation. These are exact quick-reply matches and return
`intent: "frontend_special"`, `source: "quick_reply"`.

### Quick reply buttons

The frontend suggestion buttons send exact phrases:

| Button text | Response path |
| --- | --- |
| `I'm feeling anxious` | Quick reply |
| `I need to talk` | Quick reply |
| `Breathing exercise` | Quick reply |
| `Trouble sleeping` | Quick reply |
| `Grounding technique` | Quick reply |

Quick replies are matched only after normalisation; they do not use fuzzy
matching.

### Classifier and FAQ cleanup

- Duplicate tags are canonicalised in code (`anxious` → `anxiety`,
  `stressed` → `stress`, `sad` → `sadness`, `depressed` → `depression`, and so
  on) without rewriting `data.json`.
- Factual `fact-*` and `*_info` intents are moved to the FAQ index instead of
  being treated as mental-health intents.
- Synthetic `followup_*` intents are excluded from training.
- Unknown or low-confidence text receives a deliberate unknown response rather
  than a forced mental-health answer.
- FAQ retrieval only runs for question-like text, so statements such as
  "I feel empty" are not hijacked by factual matches.

---

## 📊 Evaluation

Run the grouped holdout evaluation from the backend directory:

```bash
.venv/bin/python evaluate.py
```

The script holds out patterns by intent, removes the exact-match fast path, and
also checks off-topic and FAQ behaviour.

Current conservative baseline:

- Holdout accuracy: **30.9%**
- Holdout unknown rate: **46.9%**
- Off-topic questions answered: **0/8** (lower is better)
- FAQ questions matched: **4/4**

The low accuracy is intentional at this stage: the classifier abstains when
support is weak instead of forcing an off-topic answer. Use the printed
confusion table and per-intent misses to decide where more training data is
needed.

### Tests

```bash
cd backend
.venv/bin/python -m unittest discover -s tests -v
```

The suite covers deterministic safety, API validation, rate limiting, session
reset/deletion, classifier cleanup, FAQ retrieval, unknown handling, production
configuration, request IDs, and security headers.

---

## 📦 Requirements

- Python 3.11+
- Flask 3.0.0
- Flask-CORS 4.0.0
- Gunicorn 22.0.0
- scikit-learn 1.3.0
- numpy 1.24.3
- nltk 3.8.1

---

## 🔧 Configuration

Set these environment variables before starting the server:

| Variable | Default | Purpose |
| --- | --- | --- |
| `TOM_ENV` | `development` | `production` (or `staging`) enables fail-fast checks and HSTS. |
| `TOM_SECRET_KEY` | local development key | Flask session signing key. Production requires a random value of at least 32 characters. |
| `TOM_CORS_ORIGINS` | `*` in development | Comma-separated allowed frontend origins. Required in production; wildcards are rejected. |
| `TOM_TRUST_PROXY` | `false` | Trust one proxy hop for client IP and HTTPS scheme. Enable on Render. |
| `TOM_SESSION_TTL_SECONDS` | `1800` | Idle time before session context expires. |
| `TOM_MAX_SESSIONS` | `1000` | Maximum sessions held in memory. |
| `TOM_RATE_LIMIT_REQUESTS` | `20` | Requests allowed per session window. |
| `TOM_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding-window length. |
| `TOM_LOG_LEVEL` | `INFO` | `CRITICAL`, `DEBUG`, `ERROR`, `INFO`, or `WARNING`. |
| `TOM_HOST` | `0.0.0.0` | Development server bind address. |
| `TOM_PORT` | `8000` | Development server port. |

Context is bounded to 10 recent messages per session. The rate limiter keeps at
most `TOM_MAX_SESSIONS` keys.

Production configuration fails at import time when `TOM_ENV=production` and the
secret is missing/short, CORS origins are missing or contain `*`, the log level
is invalid, or a numeric/boolean setting cannot be parsed. This prevents a
public deployment from silently using local development defaults.

### Change the port

```bash
TOM_PORT=9000 python api_server.py
```

In production, gunicorn reads Render's `PORT` variable automatically.

### CORS

Development defaults to `*` so the Vite dev server can reach the API. In
production, list exact origins:

```bash
TOM_CORS_ORIGINS="https://tom.vercel.app,https://tom-git-main.vercel.app"
```

Credentials are disabled because the frontend sends its anonymous session
identifier in the request body. CORS is not authentication; add edge rate
limiting or authentication before a high-traffic public launch.

### Production server

Run gunicorn from the backend directory:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

The configuration uses one worker with eight threads because sessions and rate
limits are process-local. Horizontal scaling requires Redis or sticky sessions.
See [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for the Render + Vercel setup.

---

## 🧪 Testing the API with curl

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I am feeling sad", "session_id": "demo-session", "region": "IN"}'
```

```bash
curl -X POST http://127.0.0.1:8000/api/session/reset \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-session"}'
```

```bash
curl -X DELETE http://127.0.0.1:8000/api/data \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-session"}'
```

---

## 🔄 Connecting Frontend + Backend

### Step 1: Start the backend

```bash
cd backend
python api_server.py
```

### Step 2: Start the frontend

```bash
cd Frontend
npm install
npm run dev
```

### Step 3: Open the app

- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000

The frontend reads `VITE_TOM_API_URL` (or `VITE_API_BASE_URL`) and defaults to
`http://127.0.0.1:8000`.

### Frontend reliability behaviour

- Requests time out after 9 seconds and retry once for ordinary messages.
- Crisis messages and already-offline sessions use a 5-second, no-retry attempt
  so the local deterministic crisis fallback appears quickly.
- If the server is unreachable, TOM shows a clear offline reply with a retry
  action. Crisis language still gets the full crisis response and regional
  resources.
- Chat history is saved in the tab's session storage, so reloading a tab can
  restore the conversation. Consent, region, and the anonymous session ID are
  stored in local storage.
- Users can start a new conversation, clear the chat, or delete all stored data
  and withdraw consent from the privacy panel.

### Frontend tests

With Node 22:

```bash
cd Frontend
npm test
```

The tests cover deterministic safety, offline fallbacks, consent, region and
session persistence, message round-tripping, and full data deletion.

---

## 🐛 Troubleshooting

### Backend not starting

```bash
pip list | grep -E "flask|scikit|numpy|nltk"
pip install -r requirements.txt
```

### Production configuration error

If startup fails with `RuntimeError` mentioning `TOM_SECRET_KEY`,
`TOM_CORS_ORIGINS`, or another `TOM_*` variable, production validation is
working. Set the missing or valid value and restart. See
[`../DEPLOYMENT.md`](../DEPLOYMENT.md) for the required production values.

### Connection refused

- Make sure the backend is running: `python api_server.py`
- Check port 8000 is not blocked.
- Open http://127.0.0.1:8000/api/health in a browser.

### CORS errors

- Check that the frontend origin exactly matches an entry in
  `TOM_CORS_ORIGINS` (scheme, host, and port).
- In development, the default is `*`; in production, wildcards are rejected.
- Make sure Flask-CORS is installed.

---

## 📝 Notes

- Context is in memory only and expires after 30 minutes by default.
- Restarting the backend clears all sessions and rate-limit windows.
- No chat content is written to disk by the API.
- Session state is process-local. Run one gunicorn worker with threads, or move
  state to Redis before scaling horizontally.
- Rate limiting is per anonymous session ID, so add edge rate limiting for
  public, high-traffic deployments.
- See [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for production configuration,
  verification, rollback, and remaining operational work.
