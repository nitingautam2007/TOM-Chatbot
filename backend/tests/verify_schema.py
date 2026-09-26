"""Non-sensitive schema verifier: prints table/index/revision names only."""

import asyncio

from sqlalchemy import text

from app.database.connection import engine


async def main() -> None:
    async with engine.connect() as conn:
        tables = [
            r[0]
            for r in await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' ORDER BY table_name"
                )
            )
        ]
        indexes = [
            r[0]
            for r in await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname='public' ORDER BY indexname"
                )
            )
        ]
        revisions = [
            r[0]
            for r in await conn.execute(text("SELECT version_num FROM alembic_version"))
        ]
        print("TABLES:", tables)
        print("INDEXES:", indexes)
        print("ALEMBIC_REV:", revisions)


if __name__ == "__main__":
    asyncio.run(main())
