from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the process-wide async engine (one connection pool per process)."""
    return create_async_engine(
        settings.database_url,
        # Validates pooled connections before handing them out, so a Postgres
        # restart doesn't surface as a mid-request "connection closed" error.
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Session factory used by API request handlers and the agent worker."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def ping(engine: AsyncEngine) -> None:
    """Round-trip to Postgres; raises if the database is unreachable."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
