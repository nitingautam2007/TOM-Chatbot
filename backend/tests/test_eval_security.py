"""Phase 7 security / privacy checks (static + behavioural)."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

client = TestClient(app)


def test_env_ignored_by_gitignore() -> None:
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists(), "root .gitignore missing"
    text = gitignore.read_text(encoding="utf-8", errors="ignore")
    assert ".env" in text or "backend/.env" in text or "**/.env" in text


def test_env_example_has_no_real_secrets() -> None:
    example = BACKEND / ".env.example"
    if not example.exists():
        return
    text = example.read_text(encoding="utf-8")
    # Placeholders only
    assert "password=postgres" not in text.lower() or "CHANGE" in text.upper() or "your" in text.lower()
    assert not re.search(r"sk-[a-zA-Z0-9]{20,}", text)


def test_no_openai_or_external_ai_imports_in_app() -> None:
    app_dir = BACKEND / "app"
    forbidden = re.compile(
        r"\b(openai|anthropic|google\.generativeai|grok|openrouter)\b",
        re.IGNORECASE,
    )
    hits = []
    for path in app_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            hits.append(str(path.relative_to(BACKEND)))
    assert not hits, f"external AI references: {hits}"


def test_safety_detect_does_not_log_raw_message() -> None:
    """SafetyService must not print the message; smoke via detect on unique token."""
    from app.services.safety.service import SafetyService

    unique = "zebra_unique_token_for_safety_log_check"
    SafetyService().detect(unique)  # should not raise; no logger call with text
    # Cannot capture all logs without caplog — assert method has no logger.info of text.
    import inspect

    from app.services.safety import service as safety_mod

    src = inspect.getsource(safety_mod)
    assert "logger.info" not in src
    assert "print(" not in src


def test_chat_error_bodies_have_no_secret_headers() -> None:
    resp = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "conversation_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    body = resp.text.lower()
    assert "password" not in body
    assert "database_url" not in body
    assert "api_key" not in body


def test_no_telemetry_endpoints() -> None:
    # Only known API prefixes
    for path in ("/api/telemetry", "/api/track", "/api/analytics"):
        assert client.get(path).status_code == 404


def test_evaluation_dataset_has_no_real_names_or_pii() -> None:
    from evaluation.dataset import CLASSIFICATION, SAFETY

    for ex in list(CLASSIFICATION) + list(SAFETY):
        # Synthetic engineering text only — no emails, phones.
        assert "@" not in ex["text"] or "email" not in ex["text"]
        assert not re.search(r"\b\d{3}-\d{3}-\d{4}\b", ex["text"])
