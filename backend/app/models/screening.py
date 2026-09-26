import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import CreatedAtMixin

# Simple explicit screening lifecycle (Phase 5).
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


class ScreeningSession(Base, CreatedAtMixin):
    __tablename__ = "screening_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    screening_type: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_IN_PROGRESS, server_default=STATUS_IN_PROGRESS
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", back_populates="screening_sessions")
    responses = relationship(
        "ScreeningResponse",
        back_populates="screening_session",
        cascade="all, delete-orphan",
        order_by="ScreeningResponse.question_number",
    )


class ScreeningResponse(Base, CreatedAtMixin):
    __tablename__ = "screening_responses"
    __table_args__ = (
        UniqueConstraint(
            "screening_session_id",
            "question_number",
            name="uq_screening_responses_session_question",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    screening_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("screening_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    response_value: Mapped[int] = mapped_column(Integer, nullable=False)

    screening_session = relationship("ScreeningSession", back_populates="responses")
