from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.errors import ConversationNotFoundError

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Persist the exchange and return TOM's local reply.

    Thin handler: validation via Pydantic, logic in ChatService.
    No external AI service is ever called.
    """
    try:
        return await service.send_message(request.message, request.conversation_id)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
