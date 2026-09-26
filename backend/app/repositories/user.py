import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

# Serialises "get default user" so two concurrent first-time requests (e.g. the
# dashboard's conversation list and a chat send, or a StrictMode double-effect)
# cannot insert two default users — which would split conversations across users
# and silently break restore. Transaction-scoped: released on commit/rollback.
_DEFAULT_USER_LOCK = "SELECT pg_advisory_xact_lock(7272)"


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_default(self) -> User | None:
        """Single anonymous development user (no personal data collected)."""
        result = await self.session.execute(
            select(User).order_by(User.created_at.asc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_default(self) -> User:
        await self.session.execute(text(_DEFAULT_USER_LOCK))
        user = await self.get_default()
        if user is not None:
            return user
        user = User(id=uuid.uuid4())
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)
