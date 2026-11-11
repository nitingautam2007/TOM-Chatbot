#!/usr/bin/env python3
"""
TOM Backend API Server
=======================

Flask REST API for TOM - Talk To Me frontend integration.

Special handling:
- Deterministic safety checks run before quick replies and the ML model.
- Buttons and mood emojis use the frontend's curated responses.
- Text queries use TOM's canonical intents and FAQ retrieval.
- Conversation context is short lived, bounded, and in memory only.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request, session
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

from config import load_settings
from observability import (
    REQUEST_ID_HEADER,
    configure_logging,
    request_id_from_header,
)
from safety import (
    DEFAULT_REGION,
    REGION_LABELS,
    assess_safety,
    get_crisis_resources,
    normalize_text,
)
from session_store import RateLimiter, SessionStore
from tom_chatbot import TOmChatbot

TOM_VERSION = "2.0.0"

SETTINGS = load_settings()
LOG = configure_logging(SETTINGS.log_level)

# Initialize Flask app
app = Flask(__name__)
app.config.update(
    SECRET_KEY=SETTINGS.secret_key,
    MAX_CONTENT_LENGTH=SETTINGS.max_content_length,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=SETTINGS.is_production,
    PREFERRED_URL_SCHEME="https" if SETTINGS.is_production else "http",
)

if SETTINGS.trust_proxy:
    # Render terminates TLS and forwards the original client address.
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
    )

# The frontend sends an anonymous session identifier in the request body, so
# cross-origin requests do not need cookies. Keeping credentials disabled also
# avoids CSRF-style access to another browser session.
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": list(SETTINGS.cors_origins),
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", REQUEST_ID_HEADER],
            "expose_headers": [REQUEST_ID_HEADER, "Retry-After"],
            "max_age": 600,
        }
    },
)

MAX_MESSAGE_LENGTH = SETTINGS.max_message_length
MAX_SESSION_ID_LENGTH = SETTINGS.max_session_id_length

SESSION_STORE = SessionStore(
    ttl_seconds=SETTINGS.session_ttl_seconds,
    max_sessions=SETTINGS.max_sessions,
    max_messages=10,
)
RATE_LIMITER = RateLimiter(
    max_requests=SETTINGS.rate_limit_requests,
    window_seconds=SETTINGS.rate_limit_window_seconds,
    max_keys=SETTINGS.max_sessions,
)

STARTED_AT = time.monotonic()
MODEL_READY = False

# Get the absolute path to data.json
BACKEND_DIR = Path(__file__).resolve().parent
DATA_PATH = str(BACKEND_DIR / "data.json")

# Initialize TOM chatbot with explicit data path
tom = TOmChatbot(data_path=DATA_PATH)

LOG.info("Initializing TOM chatbot")
if not tom.load_data():
    raise RuntimeError("Failed to load TOM training data.")
if not tom.train_model():
    raise RuntimeError("Failed to train the TOM classifier.")

MODEL_READY = True
LOG.info(
    "TOM chatbot initialized",
    extra={
        "extra_fields": {
            "intents": len(tom.model.classes_) if tom.model is not None else 0,
            "patterns": tom.model_sample_count,
            "faq_entries": len(tom.faq_entries),
            "environment": SETTINGS.environment,
        }
    },
)

# Frontend responses for specific buttons and moods.
# These are exact matches after normalize_text().
FRONTEND_SPECIAL_RESPONSES = {
    # Mood selections (with and without emojis)
    "i'm feeling struggling today": "I hear you. Would you like to tell me more about what's on your mind?",
    "i'm feeling low today": "Thank you for sharing that with me. You're not alone in feeling this way. Would you like to talk about what's been difficult lately?",
    "i'm feeling okay today": "I appreciate you reaching out. Sometimes just checking in with yourself makes a difference. What's been on your mind today?",
    "i'm feeling good today": "That's wonderful to hear! What's making you feel good?",
    "i'm feeling great today": "That's fantastic! What's bringing you joy today?",
    # Mood selections with emojis
    "i'm feeling struggling today (😔)": "I hear you. Would you like to tell me more about what's on your mind?",
    "i'm feeling low today (😕)": "Thank you for sharing that with me. You're not alone in feeling this way. Would you like to talk about what's been difficult lately?",
    "i'm feeling okay today (😐)": "I appreciate you reaching out. Sometimes just checking in with yourself makes a difference. What's been on your mind today?",
    "i'm feeling good today (🙂)": "That's wonderful to hear! What's making you feel good?",
    "i'm feeling great today (😊)": "That's fantastic! What's bringing you joy today?",
    # Suggestion buttons (exact matches)
    "i'm feeling anxious": "Anxiety can feel overwhelming, but you're doing the right thing by acknowledging it. Let's try a simple breathing exercise: breathe in for 4 counts, hold for 4, breathe out for 6. How does that feel?",
    "i need to talk": "I'm here and I'm listening. This is a safe space — there's no right or wrong way to feel. What would you like to share?",
    "breathing exercise": "Let's do a calming box breath together:\n\n• Breathe in slowly for 4 counts\n• Hold for 4 counts\n• Breathe out for 4 counts\n• Hold for 4 counts\n\nRepeat this 4 times. Take your time — I'm right here with you.",
    "trouble sleeping": "Sleep difficulties are so common, and they can make everything feel harder. A few things that often help: keeping a consistent bedtime, avoiding screens 30 minutes before bed, and a short body-scan meditation. Would you like me to guide you through one?",
    "grounding technique": "A gentle grounding technique: the 5-4-3-2-1 method.\n\n• 5 things you can see\n• 4 things you can physically feel\n• 3 things you can hear\n• 2 things you can smell\n• 1 thing you can taste\n\nThis brings your attention back to the present moment.",
}

NORMALIZED_SPECIAL_RESPONSES = {
    normalize_text(pattern): response
    for pattern, response in FRONTEND_SPECIAL_RESPONSES.items()
}

# Accept "I am feeling ..." as well as the button's "I'm feeling ...".
for pattern, response in list(NORMALIZED_SPECIAL_RESPONSES.items()):
    if pattern.startswith("i'm feeling "):
        alias = pattern.replace("i'm feeling ", "i am feeling ", 1)
        NORMALIZED_SPECIAL_RESPONSES.setdefault(alias, response)


def get_risk_level(intent: str) -> str:
    """Determine risk level based on canonical intent."""

    if intent in ("crisis", "suicide"):
        return "high"
    return "low"


def resolve_session_id(data: dict) -> tuple[str | None, tuple | None]:
    """Validate or create a session identifier.

    Returns ``(session_id, error_response)``.
    """

    session_id = data.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        return None, invalid_request("The session identifier is not valid.")
    if isinstance(session_id, str):
        session_id = session_id.strip()
        if len(session_id) > MAX_SESSION_ID_LENGTH:
            return None, invalid_request("The session identifier is too long.")

    if not session_id:
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id

    return session_id, None


def invalid_request(message: str, status: int = 400, code: str = "invalid_request"):
    return (
        jsonify(
            {
                "error": code,
                "response": message,
                "intent": "none",
                "risk_level": "low",
                "resources": [],
                "confidence": 0.0,
                "source": "validation",
            }
        ),
        status,
    )


def rate_limited_response(session_id: str, retry_after: int):
    response, status = (
        jsonify(
            {
                "error": "rate_limited",
                "response": (
                    "You're sending messages quickly. Please wait a moment "
                    "and try again."
                ),
                "intent": "none",
                "risk_level": "low",
                "resources": [],
                "retry_after": retry_after,
                "session_id": session_id,
                "confidence": 0.0,
                "source": "rate_limit",
            }
        ),
        429,
    )
    response.headers["Retry-After"] = str(retry_after)
    return response, status


@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat endpoint for the frontend.

    Safety checks always run before quick replies, rate limiting, or the ML
    classifier. Crisis messages are therefore never blocked.
    """

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or "message" not in data:
            return invalid_request("Please send a message so I can respond.")

        user_message = data.get("message")
        if not isinstance(user_message, str):
            return invalid_request("Your message needs to be text.")
        user_message = user_message.strip()
        if not user_message:
            return invalid_request(
                "Your message was empty. What would you like to share?"
            )
        if len(user_message) > MAX_MESSAGE_LENGTH:
            return invalid_request(
                f"Please keep your message under {MAX_MESSAGE_LENGTH} characters.",
                status=413,
                code="message_too_long",
            )

        session_id, error = resolve_session_id(data)
        if error:
            return error

        region = data.get("region", DEFAULT_REGION)
        if not isinstance(region, str) or region not in REGION_LABELS:
            region = DEFAULT_REGION

        # Safety is authoritative and must run before any quick-reply, rate
        # limit, or ML path.
        safety = assess_safety(user_message)
        if safety.is_crisis:
            SESSION_STORE.append_exchange(session_id, user_message, safety.response)
            return jsonify(
                {
                    "response": safety.response,
                    "intent": "crisis",
                    "risk_level": "high",
                    "risk_reasons": [safety.reason] if safety.reason else ["crisis"],
                    "resources": get_crisis_resources(region),
                    "region": region,
                    "session_id": session_id,
                    "confidence": 1.0,
                    "source": "safety",
                }
            )

        allowed, retry_after = RATE_LIMITER.check(session_id)
        if not allowed:
            return rate_limited_response(session_id, retry_after)

        # Quick replies are exact matches only, after normalisation.
        special_response = NORMALIZED_SPECIAL_RESPONSES.get(
            normalize_text(user_message)
        )
        if special_response:
            SESSION_STORE.append_exchange(
                session_id, user_message, special_response
            )
            return jsonify(
                {
                    "response": special_response,
                    "intent": "frontend_special",
                    "risk_level": "low",
                    "resources": [],
                    "region": region,
                    "session_id": session_id,
                    "confidence": 1.0,
                    "source": "quick_reply",
                }
            )

        # The API keeps context per session, so the classifier must not use
        # its process-global conversation history.
        continuing = bool(SESSION_STORE.get_messages(session_id))
        reply = tom.generate_reply(
            user_message,
            check_safety=False,
            continuing=continuing,
        )
        SESSION_STORE.append_exchange(session_id, user_message, reply.response)

        return jsonify(
            {
                "response": reply.response,
                "intent": reply.intent,
                "risk_level": get_risk_level(reply.intent),
                "resources": [],
                "region": region,
                "session_id": session_id,
                "confidence": round(reply.confidence, 4),
                "source": reply.source,
            }
        )

    except RequestEntityTooLarge:
        return request_too_large(None)
    except Exception:
        LOG.exception(
            "Error in /api/chat",
            extra={"extra_fields": {"request_id": getattr(g, "request_id", None)}},
        )
        return (
            jsonify(
                {
                    "error": "server_error",
                    "response": (
                        "I'm having trouble responding right now. Please try again."
                    ),
                    "intent": "none",
                    "risk_level": "low",
                    "resources": [],
                    "confidence": 0.0,
                    "source": "error",
                }
            ),
            500,
        )


def _reset_session_payload(data: dict | None):
    data = data if isinstance(data, dict) else {}
    session_id, error = resolve_session_id(data)
    if error:
        return error

    SESSION_STORE.reset(session_id)
    RATE_LIMITER.reset(session_id)
    if session.get("session_id") == session_id:
        session.pop("session_id", None)
    return session_id


@app.route("/api/session/reset", methods=["POST"])
def reset_session():
    """Forget the short-lived context for one session."""

    payload = _reset_session_payload(request.get_json(silent=True))
    if isinstance(payload, tuple):
        return payload
    return jsonify({"status": "reset", "session_id": payload})


@app.route("/api/data", methods=["DELETE"])
def delete_data():
    """Delete all server-side data held for one browser session.

    TOM keeps no durable chat records. This clears the in-memory context and
    rate-limit state; the frontend clears its own local/session storage.
    """

    data = request.get_json(silent=True)
    if data is None:
        data = {"session_id": request.args.get("session_id")}
    if not isinstance(data, dict):
        return invalid_request("The request body must be a JSON object.")

    payload = _reset_session_payload(data)
    if isinstance(payload, tuple):
        return payload
    session.clear()
    return jsonify({"status": "deleted", "session_id": payload})


@app.route("/api/health", methods=["GET"])
def health():
    """Liveness check with model, session, and rate-limit metrics."""

    ready = _model_ready()
    session_stats = SESSION_STORE.stats()
    return jsonify(
        {
            "status": "online",
            "ready": ready,
            "environment": SETTINGS.environment,
            "version": TOM_VERSION,
            "model": "TOmChatbot (SVM)",
            "intents": len(tom.model.classes_) if tom.model is not None else 0,
            "patterns": tom.model_sample_count,
            "faq_entries": len(tom.faq_entries),
            "sessions": session_stats["sessions"],
            "messages": session_stats["messages"],
            "rate_limit_keys": RATE_LIMITER.stats()["tracked_keys"],
            "uptime_seconds": round(time.monotonic() - STARTED_AT, 1),
            "timestamp": _utc_timestamp(),
            "message": (
                "TOM backend is running and ready!"
                if ready
                else "TOM backend is running, but the model is not ready."
            ),
        }
    )


@app.route("/api/ready", methods=["GET"])
def readiness():
    """Readiness check used by orchestrators before routing traffic."""

    if not _model_ready():
        return (
            jsonify(
                {
                    "status": "unavailable",
                    "ready": False,
                    "error": "model_unavailable",
                }
            ),
            503,
        )
    return jsonify({"status": "ready", "ready": True})


def _model_ready() -> bool:
    return bool(MODEL_READY and tom.model is not None and tom.model_sample_count > 0)


def _utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _error_body(code: str, message: str, source: str = "validation") -> dict:
    return {
        "error": code,
        "response": message,
        "intent": "none",
        "risk_level": "low",
        "resources": [],
        "confidence": 0.0,
        "source": source,
    }


def request_too_large(error=None):
    return (
        jsonify(
            _error_body(
                "request_too_large",
                "That message is too large. Please shorten it and try again.",
            )
        ),
        413,
    )


HTTP_ERROR_CODES = {
    404: "not_found",
    405: "method_not_allowed",
    413: "request_too_large",
}

HTTP_ERROR_MESSAGES = {
    404: "That endpoint does not exist.",
    405: "That method is not allowed for this endpoint.",
    413: "That message is too large. Please shorten it and try again.",
}


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    status = error.code or 500
    code = HTTP_ERROR_CODES.get(status, "http_error")
    message = HTTP_ERROR_MESSAGES.get(
        status,
        (
            "The request could not be completed."
            if status < 500
            else "I'm having trouble responding right now. Please try again."
        ),
    )
    response = jsonify(
        _error_body(
            code,
            message,
            "validation" if status < 500 else "error",
        )
    )
    response.status_code = status

    if status == 405:
        methods = getattr(error, "valid_methods", None)
        if methods:
            response.headers["Allow"] = ", ".join(methods)

    return response


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    if isinstance(error, HTTPException):
        return handle_http_error(error)

    LOG.exception(
        "Unhandled server error",
        extra={
            "extra_fields": {
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
            }
        },
    )
    return (
        jsonify(
            _error_body(
                "server_error",
                "I'm having trouble responding right now. Please try again.",
                "error",
            )
        ),
        500,
    )


def _set_security_headers(response) -> None:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        ),
        "X-Permitted-Cross-Domain-Policies": "none",
    }
    if SETTINGS.is_production:
        headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    for name, value in headers.items():
        if name not in response.headers:
            response.headers[name] = value


@app.before_request
def begin_request():
    g.request_id = request_id_from_header(request.headers.get(REQUEST_ID_HEADER))
    g.request_started = time.perf_counter()


@app.after_request
def finish_request(response):
    request_id = getattr(g, "request_id", None) or request_id_from_header(None)
    response.headers[REQUEST_ID_HEADER] = request_id
    _set_security_headers(response)

    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"

        level = logging.INFO
        if response.status_code >= 500:
            level = (
                logging.WARNING
                if request.path == "/api/ready"
                else logging.ERROR
            )
        elif response.status_code >= 400:
            level = logging.WARNING
        elif request.method == "OPTIONS" or request.path == "/api/health":
            level = logging.DEBUG

        started = getattr(g, "request_started", None)
        LOG.log(
            level,
            "request",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": (
                        round((time.perf_counter() - started) * 1000, 2)
                        if started is not None
                        else None
                    ),
                    "remote_addr": request.remote_addr,
                }
            },
        )

    return response


if __name__ == "__main__":
    if SETTINGS.is_production:
        raise SystemExit(
            "Refusing to start the Flask development server in production. "
            "Use: gunicorn --worker-class gthread --workers 1 --threads 8 "
            "wsgi:app"
        )

    print("\n" + "=" * 60)
    print("TOM Backend API Server with Context Memory")
    print("=" * 60)
    print("\nStarting Flask server...")
    print(f"API will be available at: http://{SETTINGS.host}:{SETTINGS.port}")
    print("\nEndpoints:")
    print("  POST   /api/chat            - Send user messages")
    print("  POST   /api/session/reset   - Forget one session's context")
    print("  DELETE /api/data            - Delete one session's server data")
    print("  GET    /api/health          - Health check and model metrics")
    print("  GET    /api/ready           - Readiness check")
    print("\nFeatures:")
    print("  - Deterministic crisis handling before every other path")
    print("  - Exact-match quick replies")
    print("  - Canonical intents, FAQ retrieval, and unknown handling")
    print("  - Bounded context memory with a 30 minute TTL")
    print("  - Per-session rate limiting (crisis messages exempt)")
    print("\n" + "=" * 60 + "\n")

    app.run(host=SETTINGS.host, port=SETTINGS.port, debug=False)
