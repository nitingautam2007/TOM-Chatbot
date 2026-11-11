"""Gunicorn configuration for the TOM API.

TOM keeps session context and rate-limit counters in process memory. Run a
single worker with multiple threads so every request sees the same state. If
the API is scaled horizontally, move that state to Redis (or use sticky
sessions) before increasing ``workers``.
"""

from __future__ import annotations

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
worker_class = "gthread"
threads = int(os.environ.get("TOM_GUNICORN_THREADS", "8"))

timeout = 60
graceful_timeout = 30
keepalive = 5

# Application request logs are emitted as structured JSON by
# backend/observability.py, so gunicorn's duplicate access log stays disabled.
accesslog = None
errorlog = "-"
loglevel = os.environ.get("TOM_LOG_LEVEL", "INFO").lower()

# Recycle workers only after many requests. Restarting a worker clears its
# in-memory sessions, so this is deliberately high.
max_requests = 10_000
max_requests_jitter = 500
