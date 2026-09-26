import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin


class User(Base, TimestampMixin):
    """Minimal app user. No personal information is collected."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    mood_checkins = relationship(
        "MoodCheckin", back_populates="user", cascade="all, delete-orphan"
    )
    screening_sessions = relationship(
        "ScreeningSession", back_populates="user", cascade="all, delete-orphan"
    )
