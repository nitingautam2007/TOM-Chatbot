import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScreeningResponse, ScreeningSession
from app.models.screening import STATUS_IN_PROGRESS


class ScreeningRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        user_id: uuid.UUID,
        screening_type: str,
        score: int | None = None,
        severity: str | None = None,
    ) -> ScreeningSession:
        session_row = ScreeningSession(
            id=uuid.uuid4(),
            user_id=user_id,
            screening_type=screening_type,
            score=score,
            severity=severity,
            status=STATUS_IN_PROGRESS,
        )
        self.session.add(session_row)
        await self.session.flush()
        return session_row

    async def get_session(self, session_id: uuid.UUID) -> ScreeningSession | None:
        return await self.session.get(ScreeningSession, session_id)

    async def get_in_progress(
        self, user_id: uuid.UUID, screening_type: str
    ) -> ScreeningSession | None:
        result = await self.session.execute(
            select(ScreeningSession)
            .where(
                ScreeningSession.user_id == user_id,
                ScreeningSession.screening_type == screening_type,
                ScreeningSession.status == STATUS_IN_PROGRESS,
            )
            .order_by(ScreeningSession.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add_response(
        self,
        screening_session_id: uuid.UUID,
        question_number: int,
        response_value: int,
    ) -> ScreeningResponse:
        response = ScreeningResponse(
            id=uuid.uuid4(),
            screening_session_id=screening_session_id,
            question_number=question_number,
            response_value=response_value,
        )
        self.session.add(response)
        await self.session.flush()
        return response

    async def list_responses(
        self, screening_session_id: uuid.UUID
    ) -> list[ScreeningResponse]:
        result = await self.session.execute(
            select(ScreeningResponse)
            .where(ScreeningResponse.screening_session_id == screening_session_id)
            .order_by(ScreeningResponse.question_number.asc())
        )
        return list(result.scalars().all())
