"""Environment-driven configuration for TOM.

The defaults are for local development.  Production deployments should set
``TOM_ENV=production`` plus an explicit secret key and CORS allowlist.  Invalid
production configuration fails at import time rather than starting a server
with unsafe defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse

DEFAULT_SECRET_KEY = "tom-local-development-key"
DEVELOPMENT_ENVIRONMENTS = {"dev", "development", "test", "testing"}
PRODUCTION_ENVIRONMENTS = {"prod", "production", "staging"}
VALID_ENVIRONMENTS = DEVELOPMENT_ENVIRONMENTS | PRODUCTION_ENVIRONMENTS
LOG_LEVELS = {"CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING"}


def _env_int(
    environ: Mapping[str, str],
    name: str,
    default: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    raw = environ.get(name)
    if raw is None or str(raw).strip() == "":
        value = default
    else:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"{name} must be an integer, got {raw!r}."
            ) from error

    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be at most {maximum}.")
    return value


def _env_bool(
    environ: Mapping[str, str],
    name: str,
    default: bool = False,
) -> bool:
    raw = environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default

    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(
        f"{name} must be a boolean (true/false), got {raw!r}."
    )


def _parse_cors_origins(
    raw: str | None,
    *,
    is_production: bool,
) -> tuple[str, ...]:
    if not raw or not raw.strip():
        if is_production:
            raise RuntimeError(
                "TOM_CORS_ORIGINS must list the frontend origin(s) when "
                "TOM_ENV=production."
            )
        return ("*",)

    origins = tuple(
        dict.fromkeys(
            origin.strip().rstrip("/")
            for origin in raw.split(",")
            if origin.strip()
        )
    )
    if not origins:
        raise RuntimeError("TOM_CORS_ORIGINS did not contain a valid origin.")

    if "*" in origins:
        if is_production:
            raise RuntimeError(
                "TOM_CORS_ORIGINS cannot contain '*' in production. List the "
                "exact frontend origin instead."
            )
        return ("*",)

    for origin in origins:
        parsed = urlparse(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or any(character.isspace() for character in origin)
        ):
            raise RuntimeError(
                f"Invalid CORS origin {origin!r}. Use a value such as "
                "'https://tom.example.com'."
            )
    return origins


@dataclass(frozen=True)
class Settings:
    environment: str
    is_production: bool
    secret_key: str
    cors_origins: tuple[str, ...]
    trust_proxy: bool
    session_ttl_seconds: int
    max_sessions: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    log_level: str
    host: str
    port: int

    @property
    def max_content_length(self) -> int:
        return 32 * 1024

    @property
    def max_message_length(self) -> int:
        return 2000

    @property
    def max_session_id_length(self) -> int:
        return 128


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Read and validate settings from an environment mapping."""

    values = os.environ if environ is None else environ
    environment = str(values.get("TOM_ENV", "development")).strip().lower()
    if not environment:
        environment = "development"
    if environment not in VALID_ENVIRONMENTS:
        raise RuntimeError(
            f"Invalid TOM_ENV {environment!r}. Use one of "
            f"{', '.join(sorted(VALID_ENVIRONMENTS))}."
        )
    is_production = environment in PRODUCTION_ENVIRONMENTS

    secret_key = str(values.get("TOM_SECRET_KEY", "")).strip()
    if not secret_key:
        if is_production:
            raise RuntimeError(
                "TOM_SECRET_KEY is required when TOM_ENV=production. Set a "
                "random value of at least 32 characters."
            )
        secret_key = DEFAULT_SECRET_KEY
    if is_production and (
        secret_key == DEFAULT_SECRET_KEY or len(secret_key) < 32
    ):
        raise RuntimeError(
            "TOM_SECRET_KEY must be a random value of at least 32 characters "
            "when TOM_ENV=production."
        )

    cors_origins = _parse_cors_origins(
        values.get("TOM_CORS_ORIGINS"),
        is_production=is_production,
    )

    log_level = str(values.get("TOM_LOG_LEVEL", "INFO")).strip().upper()
    if log_level not in LOG_LEVELS:
        raise RuntimeError(
            f"Invalid TOM_LOG_LEVEL {log_level!r}. Use one of "
            f"{', '.join(sorted(LOG_LEVELS))}."
        )

    return Settings(
        environment=environment,
        is_production=is_production,
        secret_key=secret_key,
        cors_origins=cors_origins,
        trust_proxy=_env_bool(values, "TOM_TRUST_PROXY", False),
        session_ttl_seconds=_env_int(
            values, "TOM_SESSION_TTL_SECONDS", 30 * 60
        ),
        max_sessions=_env_int(values, "TOM_MAX_SESSIONS", 1000),
        rate_limit_requests=_env_int(values, "TOM_RATE_LIMIT_REQUESTS", 20),
        rate_limit_window_seconds=_env_int(
            values, "TOM_RATE_LIMIT_WINDOW_SECONDS", 60
        ),
        log_level=log_level,
        host=str(values.get("TOM_HOST", "0.0.0.0")).strip() or "0.0.0.0",
        port=_env_int(values, "TOM_PORT", 8000, maximum=65535),
    )


__all__ = [
    "DEFAULT_SECRET_KEY",
    "DEVELOPMENT_ENVIRONMENTS",
    "LOG_LEVELS",
    "PRODUCTION_ENVIRONMENTS",
    "Settings",
    "VALID_ENVIRONMENTS",
    "load_settings",
]
