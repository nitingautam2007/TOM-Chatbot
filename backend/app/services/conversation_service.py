from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ConversationRepository, MessageRepository, UserRepository
from app.schemas.conversation import ConversationCreate, ConversationOut, MessageOut
from app.services.errors import ConversationNotFoundError


class ConversationService:
    """Conversation retrieval/creation. All DB access lives in repositories."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)

    async def list_conversations(self) -> list[ConversationOut]:
        user = await self.users.get_or_create_default()
        conversations = await self.conversations.list_for_user(user.id)
        return [ConversationOut.model_validate(c) for c in conversations]

    async def get_conversation(self, conversation_id: UUID) -> ConversationOut:
        conversation = await self.conversations.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return ConversationOut.model_validate(conversation)

    async def list_messages(self, conversation_id: UUID) -> list[MessageOut]:
        conversation = await self.conversations.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        messages = await self.messages.list_for_conversation(conversation_id)
        return [MessageOut.model_validate(m) for m in messages]

    async def create_conversation(self, payload: ConversationCreate) -> ConversationOut:
        user = await self.users.get_or_create_default()
        conversation = await self.conversations.create(user.id, payload.title)
        await self.session.commit()
        return ConversationOut.model_validate(conversation)
