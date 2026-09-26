from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreate(BaseModel):
    """Payload accepted by POST /api/conversations."""

    title: str | None = Field(default=None, max_length=200)

    @field_validator("title", mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        # Blank titles would render as empty rows in the conversation list.
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime
    # True for assistant replies from the safety library (see Message model).
    is_safety: bool = False
