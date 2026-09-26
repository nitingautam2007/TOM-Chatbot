from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url

# backend/ directory — .env is resolved regardless of the process CWD.
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _normalize_database_url(url: str) -> str:
    """Re-encode the password when it contains '@' so SQLAlchemy parses the host correctly.

    The raw password stays in backend/.env (never logged). If the URL already
    parses cleanly it is left untouched, so pre-encoded passwords are safe.
    Passwords containing '#', '/' or '?' must be percent-encoded in .env.
    """
    if not url or "://" not in url:
        return url
    try:
        parsed = make_url(url)
        if "@" not in (parsed.host or ""):
            return url  # host parsed correctly — do not touch (no double-encoding)
    except Exception:
        return url

    try:
        parts = urlparse(url)
        hostname = parts.hostname
        if not hostname or "@" in hostname:
            return url  # cannot reconstruct safely; fail later with a clear DB error
        userinfo = f"{quote(parts.username or '', safe='')}:{quote(parts.password or '', safe='')}"
        if ":" in hostname:  # IPv6 literal
            hostname = f"[{hostname}]"
        netloc = f"{userinfo}@{hostname}"
        if parts.port:
            netloc += f":{parts.port}"
        return urlunparse((parts.scheme, netloc, parts.path, "", parts.query, ""))
    except Exception:
        return url


class Settings(BaseSettings):
    """Application settings. Values can be overridden via environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="TOM_",
        env_file=str(BACKEND_DIR / ".env"),
        extra="ignore",
    )

    app_name: str = "TOM"
    app_description: str = "Privacy-focused mental health support chatbot"
    version: str = "0.10.0-phase10"
    environment: str = "development"

    # CORS — local React dev server only (IPv4 + IPv6 localhost forms)
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
    ]

    # PostgreSQL via async SQLAlchemy (Phase 2).
    # Set TOM_DATABASE_URL in backend/.env — never hardcode credentials.
    database_url: str = ""

    # Phase 3A — local multilingual embedding model (CPU-only, no API keys).
    # Hugging Face cache lives under ~/.cache/huggingface by default.
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_device: str = "cpu"

    # Phase 3B — prototype classifier thresholds (similarity-derived, NOT
    # clinically calibrated probabilities). Tuning required on real labeled
    # data later — see docs/architecture.md.
    intent_confidence_threshold: float = 0.40
    emotion_confidence_threshold: float = 0.40
    classification_ambiguity_margin: float = 0.02

    # Phase 4 — crisis resources (placeholders only; operators must set real
    # local numbers/links in backend/.env). Never invent emergency numbers.
    # TOM_SAFETY_EMERGENCY_NUMBER / TOM_SAFETY_CRISIS_RESOURCE_URL
    safety_emergency_number: str = ""
    safety_crisis_resource_url: str = ""

    # Phase 6 — local response selection (no external APIs).
    # Recent-message window fed into ResponseSelector (session context only).
    response_context_window: int = 8
    # Conservative cosine threshold for MiniLM semantic fallback (0 disables).
    response_semantic_threshold: float = 0.42

    @model_validator(mode="after")
    def _fix_database_url(self) -> "Settings":
        if self.database_url:
            self.database_url = _normalize_database_url(self.database_url)
        return self


settings = Settings()
