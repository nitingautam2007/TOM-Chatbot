import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MoodCheckin


class MoodCheckinRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        mood_score: int,
        stress_level: int,
        sleep_hours: float,
        energy_level: int,
        notes: str | None = None,
    ) -> MoodCheckin:
        checkin = MoodCheckin(
            id=uuid.uuid4(),
            user_id=user_id,
            mood_score=mood_score,
            stress_level=stress_level,
            sleep_hours=sleep_hours,
            energy_level=energy_level,
            notes=notes,
        )
        self.session.add(checkin)
        await self.session.flush()
        return checkin

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 100) -> list[MoodCheckin]:
        result = await self.session.execute(
            select(MoodCheckin)
            .where(MoodCheckin.user_id == user_id)
            .order_by(MoodCheckin.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
