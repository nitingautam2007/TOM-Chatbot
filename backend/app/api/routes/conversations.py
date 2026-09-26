from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationOut, MessageOut
from app.services.conversation_service import ConversationService
from app.services.errors import ConversationNotFoundError

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Conversation not found")


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> list[ConversationOut]:
    return await service.list_conversations()


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    payload: ConversationCreate | None = None,
) -> ConversationOut:
    return await service.create_conversation(payload or ConversationCreate())


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationOut:
    try:
        return await service.get_conversation(conversation_id)
    except ConversationNotFoundError:
        raise _not_found()


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: UUID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> list[MessageOut]:
    try:
        return await service.list_messages(conversation_id)
    except ConversationNotFoundError:
        raise _not_found()
