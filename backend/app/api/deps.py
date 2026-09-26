from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_session
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.nlp.service import NLPService, get_nlp_service_singleton
from app.services.safety.service import SafetyService, get_safety_service_singleton
from app.services.screening_service import ScreeningService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_nlp_service() -> NLPService:
    """Phase 3A NLP service (lazy model — loads on first process())."""
    return get_nlp_service_singleton()


def get_safety_service() -> SafetyService:
    """Phase 4 rule-based safety service (stateless singleton)."""
    return get_safety_service_singleton()


def get_chat_service(
    session: SessionDep,
    safety: Annotated[SafetyService, Depends(get_safety_service)],
    nlp: Annotated[NLPService, Depends(get_nlp_service)],
) -> ChatService:
    return ChatService(session, safety, nlp=nlp)


def get_conversation_service(session: SessionDep) -> ConversationService:
    return ConversationService(session)


def get_screening_service(
    session: SessionDep,
    safety: Annotated[SafetyService, Depends(get_safety_service)],
) -> ScreeningService:
    """Phase 5 PHQ-9 screening (reuses SafetyService for item-9 routing)."""
    return ScreeningService(session, safety)


__all__ = [
    "get_session",
    "get_nlp_service",
    "get_safety_service",
    "get_chat_service",
    "get_conversation_service",
    "get_screening_service",
]
