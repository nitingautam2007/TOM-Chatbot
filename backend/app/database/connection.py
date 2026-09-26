from collections.abc import AsyncIterator

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.errors import DatabaseNotConfiguredError


def _build():
    """Create engine + session factory, or (None, None) if not configured.

    Never logs or raises with the URL — credentials must not leak.
    NullPool: connections are not reused across event loops, which keeps
    uvicorn, TestClient and asyncio.run() test helpers safely isolated.
    """
    url = settings.database_url
    if not url:
        return None, None
    engine = create_async_engine(url, echo=False, poolclass=pool.NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


engine, session_factory = _build()


def db_not_configured_message() -> str:
    return (
        "Database is not configured. Create backend/.env from backend/.env.example "
        "and set TOM_DATABASE_URL (never hardcode credentials)."
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield a request-scoped async DB session."""
    if session_factory is None:
        raise DatabaseNotConfiguredError(db_not_configured_message())
    async with session_factory() as session:
        yield session
