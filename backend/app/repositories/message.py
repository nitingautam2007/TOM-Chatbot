import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        is_safety: bool = False,
    ) -> Message:
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            is_safety=is_safety,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_for_conversation(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[Message]:
        """Messages for a conversation in chronological order.

        `limit` takes the most recent N (fetched newest-first, returned oldest-
        first) — the chat path only ever needs the context window, and loading
        the whole transcript on every turn grows unbounded.
        """
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        if limit is None:
            stmt = stmt.order_by(Message.created_at.asc(), Message.id.asc())
            result = await self.session.execute(stmt)
            return list(result.scalars().all())

        stmt = (
            stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(reversed(list(result.scalars().all())))
