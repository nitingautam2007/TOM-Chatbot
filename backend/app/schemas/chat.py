from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Payload accepted by POST /api/chat."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user's message.",
        examples=["I've been feeling a bit low lately"],
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation to append to. Omit to start a new one.",
    )

    @field_validator("message")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be empty")
        return value


class ChatResponse(BaseModel):
    """Payload returned by POST /api/chat."""

    conversation_id: str = Field(..., description="Conversation this exchange belongs to")
    message: str = Field(..., description="Echo of the original user message")
    response: str = Field(..., description="TOM's reply")
    is_safety: bool = Field(
        default=False,
        description="True when the reply came from the safety (crisis) library",
    )
    suggest_exercise: bool = Field(
        default=False,
        description=(
            "True when TOM offers a short stress-relief exercise after a "
            "normal stress/support reply (never on safety replies)"
        ),
    )


class HealthResponse(BaseModel):
    """Payload returned by GET /api/health."""

    status: str
    service: str
    version: str
