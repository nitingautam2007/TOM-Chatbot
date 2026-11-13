#!/usr/bin/env python3
"""
In-memory session context storage and rate limiter for TOM API.
Provides bounded message history and sliding-window rate limiting.
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Callable, Deque

Clock = Callable[[], float]


@dataclass
class _Session:
    messages: Deque[dict]
    created_at: float
    last_seen: float


class SessionStore:
    """Bounded in-memory conversation context storage with TTL expiration."""

    def __init__(
        self,
        ttl_seconds: float = 30 * 60,
        max_sessions: int = 1000,
        max_messages: int = 10,
        clock: Clock | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_sessions <= 0:
            raise ValueError("max_sessions must be positive")
        if max_messages <= 0:
            raise ValueError("max_messages must be positive")

        self.ttl_seconds = float(ttl_seconds)
        self.max_sessions = int(max_sessions)
        self.max_messages = int(max_messages)
        self._clock = clock or time.monotonic
        self._sessions: OrderedDict[str, _Session] = OrderedDict()
        self._lock = threading.Lock()

    def _prune_locked(self, now: float) -> None:
        expired = [
            session_id
            for session_id, entry in self._sessions.items()
            if now - entry.last_seen > self.ttl_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)

        while len(self._sessions) > self.max_sessions:
            self._sessions.popitem(last=False)

    def get_messages(self, session_id: str) -> list[dict]:
        """Return message history for the given session."""
        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            entry = self._sessions.get(session_id)
            if entry is None:
                return []
            entry.last_seen = now
            self._sessions.move_to_end(session_id)
            return [dict(message) for message in entry.messages]

    def append_exchange(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str | None = None,
    ) -> None:
        """Append user message and assistant reply to the session history."""
        if not session_id:
            return

        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            entry = self._sessions.get(session_id)
            if entry is None:
                entry = _Session(
                    messages=deque(maxlen=self.max_messages),
                    created_at=now,
                    last_seen=now,
                )
                self._sessions[session_id] = entry
            entry.last_seen = now
            entry.messages.append({"role": "user", "text": user_message})
            if assistant_message:
                entry.messages.append({"role": "assistant", "text": assistant_message})
            self._sessions.move_to_end(session_id)
            self._prune_locked(now)

    def reset(self, session_id: str) -> bool:
        """Clear context for one specific session."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def stats(self) -> dict[str, int]:
        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            return {
                "sessions": len(self._sessions),
                "messages": sum(len(entry.messages) for entry in self._sessions.values()),
            }


class RateLimiter:
    """Sliding-window rate limiter per session key."""

    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: float = 60,
        max_keys: int = 1000,
        clock: Clock | None = None,
    ) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_keys <= 0:
            raise ValueError("max_keys must be positive")

        self.max_requests = int(max_requests)
        self.window_seconds = float(window_seconds)
        self.max_keys = int(max_keys)
        self._clock = clock or time.monotonic
        self._events: OrderedDict[str, Deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def _prune_locked(self, now: float) -> None:
        cutoff = now - self.window_seconds
        stale_keys: list[str] = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                stale_keys.append(key)
        for key in stale_keys:
            self._events.pop(key, None)

    def check(self, key: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, retry_after_seconds)."""
        now = self._clock()
        with self._lock:
            self._prune_locked(now)

            events = self._events.get(key)
            if events is None:
                if len(self._events) >= self.max_keys:
                    self._events.popitem(last=False)
                events = deque()
                self._events[key] = events

            cutoff = now - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.max_requests:
                retry_after = max(
                    1,
                    math.ceil(events[0] + self.window_seconds - now),
                )
                self._events.move_to_end(key)
                return False, retry_after

            events.append(now)
            self._events.move_to_end(key)
            return True, 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def stats(self) -> dict[str, int]:
        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            return {"tracked_keys": len(self._events)}


__all__ = ["RateLimiter", "SessionStore"]
