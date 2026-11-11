"""Structured logging and request metadata helpers for the TOM API.

Request logs intentionally contain metadata only.  Chat message content is not
included in the request log.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class JsonFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        fields = getattr(record, "extra_fields", None)
        if isinstance(fields, Mapping):
            payload.update(fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure the TOM logger once and return it."""

    logger = logging.getLogger("tom.api")
    logger.setLevel(level.upper())
    logger.propagate = False

    has_json_handler = any(
        isinstance(handler.formatter, JsonFormatter)
        for handler in logger.handlers
    )
    if not has_json_handler:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


def request_id_from_header(value: str | None) -> str:
    """Reuse a safe client request ID or generate a new one."""

    if value:
        candidate = value.strip()
        if REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate
    return uuid.uuid4().hex


__all__ = [
    "JsonFormatter",
    "REQUEST_ID_HEADER",
    "REQUEST_ID_PATTERN",
    "configure_logging",
    "request_id_from_header",
]
