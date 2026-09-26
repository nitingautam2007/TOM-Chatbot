from uuid import UUID

__all__ = [
    "ConversationNotFoundError",
    "DatabaseNotConfiguredError",
    "EmptyTextError",
    "NLPUnavailableError",
    "ScreeningNotFoundError",
    "ScreeningStateError",
]


class DatabaseNotConfiguredError(Exception):
    """Raised when TOM_DATABASE_URL is missing (mapped to HTTP 503)."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ConversationNotFoundError(Exception):
    """Raised when a conversation does not exist (mapped to HTTP 404)."""

    def __init__(self, conversation_id: UUID | str):
        self.conversation_id = conversation_id
        super().__init__(f"Conversation not found: {conversation_id}")


class ScreeningNotFoundError(Exception):
    """Raised when a screening does not exist or is not owned by the caller (404)."""

    def __init__(self, screening_id: UUID | str):
        self.screening_id = screening_id
        super().__init__(f"Screening not found: {screening_id}")


class ScreeningStateError(Exception):
    """Raised on an invalid screening lifecycle transition (mapped to HTTP 409)."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NLPUnavailableError(Exception):
    """Raised when the local NLP/embedding layer cannot process text.

    Mapped to HTTP 503. Chat (`/api/chat`) remains usable when this happens —
    NLP is an optional layer, never a hard dependency of the reply path.
    """

    def __init__(self, reason: str = "NLP service is unavailable"):
        self.reason = reason
        super().__init__(reason)


class EmptyTextError(Exception):
    """Raised when input text is empty or whitespace-only."""

    def __init__(self) -> None:
        super().__init__("Text must not be empty")
