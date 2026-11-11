# Deploying TOM

Production topology:

- **Backend:** Flask API on [Render](https://render.com), served by gunicorn.
- **Frontend:** React/Vite static build on [Vercel](https://vercel.com).
- **State:** short-lived, in process memory only. TOM has no database.

Both services deploy from this GitHub repository. `render.yaml` and
`Frontend/vercel.json` hold the platform configuration.

> TOM is a support tool, not emergency care. Keep the in-app crisis resources
> working and review them against current local helpline information before a
> public launch.

---

## 1. Deploy the backend on Render

1. In Render, choose **New > Blueprint** and connect this repository.
2. Render reads `render.yaml` and creates the `tom-api` web service.
3. When prompted for `TOM_CORS_ORIGINS`, enter a temporary HTTPS origin such
   as `https://placeholder.vercel.app`. You will replace it after the frontend
   is deployed. A wildcard `*` is rejected in production.
4. Deploy the service and copy its URL, for example
   `https://tom-api.onrender.com`.

Render generates `TOM_SECRET_KEY` automatically. Do not reuse a local key.

### Backend environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `TOM_ENV` | yes | Set to `production`. Enables fail-fast validation and HSTS. `staging` is treated the same way. |
| `TOM_SECRET_KEY` | yes | Random Flask signing key, at least 32 characters. |
| `TOM_CORS_ORIGINS` | yes | Comma-separated frontend origins, for example `https://tom.vercel.app`. No `*`. |
| `TOM_TRUST_PROXY` | yes | `1` on Render so client IPs and HTTPS scheme are read from proxy headers. |
| `TOM_LOG_LEVEL` | no | `INFO` by default. Use `DEBUG` only while troubleshooting. |
| `TOM_SESSION_TTL_SECONDS` | no | Idle session lifetime, default `1800`. |
| `TOM_MAX_SESSIONS` | no | In-memory session cap, default `1000`. |
| `TOM_RATE_LIMIT_REQUESTS` | no | Requests per session window, default `20`. |
| `TOM_RATE_LIMIT_WINDOW_SECONDS` | no | Rate-limit window, default `60`. |
| `TOM_GUNICORN_THREADS` | no | Request threads, default `8`. |
| `PYTHON_VERSION` | yes | `3.11.17`, matching local development. |

The service fails to start if production settings are incomplete or invalid.
That is intentional: a misconfigured public deployment should not boot with a
development secret or open CORS.

---

## 2. Deploy the frontend on Vercel

1. Import this repository into Vercel.
2. Set **Root Directory** to `Frontend`.
3. Keep the framework preset as **Vite**. `Frontend/vercel.json` sets the build
   command, output directory, SPA fallback, and security headers.
4. Add this environment variable for the **Production** environment:
   - `VITE_TOM_API_URL=https://tom-api.onrender.com`
5. Deploy and copy the production URL, for example
   `https://tom.vercel.app`.

`VITE_API_BASE_URL` is accepted as a fallback name, but new deployments should
use `VITE_TOM_API_URL`.

Environment variables are baked into the static build. After changing the API
URL, redeploy the frontend.

---

## 3. Connect the two services

1. Return to Render and update `TOM_CORS_ORIGINS` to the real Vercel origin.
   To allow preview deployments, add each preview origin as a separate
   comma-separated value or use a dedicated preview domain.
2. Redeploy the backend.
3. In the live frontend, verify:
   - consent screen and privacy panel
   - a normal chat reply
   - a mood button or quick reply
   - a crisis phrase shows regional resources immediately
   - starting a new conversation and deleting data
   - `/api/health` and `/api/ready` on the Render URL

If the browser reports a CORS error, the origin in `TOM_CORS_ORIGINS` does not
exactly match the frontend URL (scheme, host, and port must match).

---

## 4. Verify a production backend

Check liveness and readiness:

```bash
curl -sS https://tom-api.onrender.com/api/health
curl -sS https://tom-api.onrender.com/api/ready
```

A healthy response includes `"status":"online"`, `"ready":true`,
`"environment":"production"`, model metrics, and an uptime value. Every API
response includes `X-Request-ID`; use it when correlating a user report with
Render logs.

Send a test message:

```bash
curl -sS https://tom-api.onrender.com/api/chat \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://tom.vercel.app' \
  -d '{"message":"I feel sad","session_id":"deploy-check","region":"IN"}'
```

Expected headers include `Access-Control-Allow-Origin` for the configured
frontend origin, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, and `Strict-Transport-Security`.

---

## 5. Production behavior and limits

### Single instance by design

Session context and rate-limit counters live in process memory. The gunicorn
configuration therefore uses **one worker with multiple threads**:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

Do not increase `workers` without moving shared state to Redis or using sticky
sessions. Running multiple workers or instances would give each process a
separate view of sessions and rate limits. A restart or deploy clears all
in-memory sessions.

### Rate limiting

The per-session limit defaults to 20 requests per 60 seconds. Crisis messages
run through the deterministic safety layer before the limiter and are never
blocked. Because sessions are anonymous and client-supplied, a determined
abuser can rotate session IDs; add edge rate limiting (Cloudflare, Render
proxy rules, or Vercel WAF) before high-traffic public use.

### Logging and privacy

Application logs are JSON objects with request metadata only: request ID,
method, path, status, duration, and remote address. Request logs never include
chat message content. TOM does not write chats to disk and has no analytics or
crash reporting service configured.

### Health checks

- `GET /api/health` is the liveness endpoint used by Render. It always returns
  `200` while the process is running and reports `ready` plus model metrics.
- `GET /api/ready` returns `200` only when the model is loaded, otherwise `503`.
  Point stricter orchestration checks here.

Model loading and training happen during worker boot. On a sleeping free Render
instance, the first request after wake-up is slower while the worker starts.
The Render build downloads the NLTK tokenizer and WordNet data so a cold start
does not need to fetch it again; if that cache is unavailable, the application
downloads it during boot.

### Security headers

The API sends `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, a restrictive `Content-Security-Policy`, and
`Cache-Control: no-store`. Production also sends HSTS. The static frontend
sends its own headers from `Frontend/vercel.json`.

---

## 6. CI

`.github/workflows/ci.yml` runs on every pull request and push to `main`:

- backend: Python 3.11, dependencies, NLTK data, and the full unittest suite
- frontend: Node 22, `npm ci`, TypeScript check, tests, and production build

A deployment should only be promoted after both jobs pass.

---

## 7. Local production check

From `backend/`:

```bash
export TOM_ENV=production
export TOM_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export TOM_CORS_ORIGINS="http://localhost:5173"
export PORT=8000
gunicorn --config gunicorn.conf.py wsgi:app
```

Then run the frontend against it:

```bash
cd Frontend
VITE_TOM_API_URL=http://127.0.0.1:8000 npm run dev
```

Running `python api_server.py` in production mode is blocked on purpose; use
gunicorn.

---

## 8. Rollback

- **Render:** open the service, choose **Deploys**, and redeploy the previous
  successful build. Environment variable changes require a redeploy.
- **Vercel:** open **Deployments** and promote the previous production build.
- **Configuration incident:** rotate `TOM_SECRET_KEY` (this invalidates Flask
  session cookies) and redeploy. TOM's anonymous session IDs are stored by the
  browser, so chat sessions continue with a new server-side context.

---

## 9. Remaining operational work

These are not blockers for a small, supervised launch, but should be planned:

- durable/shared session storage if horizontal scaling is needed
- authentication or signed session tokens for stronger abuse control
- alerting (Render health checks and log drains, or Sentry)
- dependency and container/security scanning
- a reviewed privacy policy and retention statement for the target jurisdiction
- periodic review of crisis resources and model evaluation
