"""Async SQLAlchemy engine and session factory.

Why async?
- FastAPI is async-first. If we use a sync DB driver, every database
  query blocks the event loop — meaning no other request can be served
  while we wait for Postgres to respond.
- asyncpg is the fastest Python Postgres driver, and SQLAlchemy 2.x
  has first-class async support via create_async_engine.

Why expire_on_commit=False?
- After a commit, SQLAlchemy normally "expires" all loaded attributes,
  meaning the next attribute access triggers a lazy load (another DB call).
  In async code, lazy loading is forbidden (it would need a sync call
  inside the event loop). Setting expire_on_commit=False keeps the data
  available after commit without extra queries.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL statements when DEBUG=true
    pool_size=5,  # Keep 5 connections open in the pool
    max_overflow=10,  # Allow up to 10 more under load
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session.

    Usage in a route:
        @router.get("/things")
        async def list_things(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed when the request finishes,
    even if an exception occurs (that's what 'finally' guarantees).
    This is the dependency injection pattern — the route doesn't create
    or manage the session, it just receives one.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
