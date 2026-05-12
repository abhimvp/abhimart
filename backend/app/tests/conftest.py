"""Pytest fixtures for AbhiMart API tests.

Test isolation strategy: the "rollback" pattern.
- One test engine per session (tables created once, dropped once)
- One connection per test, wrapped in a transaction
- After each test: conn.rollback() undoes everything the test did
- No need to truncate tables between tests

Why NullPool?
SQLAlchemy's normal pool reuses connections. In the rollback pattern,
we need each fixture to get a fresh connection — NullPool disables
connection reuse, so each engine.connect() gets a new one.

Why join_transaction_mode="create_savepoint"?
Routes call db.commit(). Normally that commits to Postgres.
In tests, we need commit() to be a no-op (so rollback can undo it).
create_savepoint makes commit() release a savepoint instead of
truly committing, so the outer conn.rollback() still undoes everything.
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models.base import Base

settings = get_settings()

# Derive test DB URL: same host/user/password, different database name.
# Override by setting TEST_DATABASE_URL in environment.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    settings.DATABASE_URL.rsplit("/", 1)[0] + "/abhimart_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create the test engine once for the whole test session.

    scope="session" means this fixture runs once — tables are created
    at the start, dropped at the end. Individual tests don't pay the
    overhead of schema creation.
    """
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # clean slate
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provide a database session that auto-rolls back after each test.

    The pattern:
    1. Open a connection to the test DB
    2. Begin a real transaction (T1) on that connection
    3. Create a Session bound to that connection, with create_savepoint mode
       - session.commit() inside routes → RELEASE SAVEPOINT (not real commit)
       - The data is visible within T1 but not truly committed
    4. After the test: conn.rollback() → rolls back T1 → all test data gone
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        yield session
        await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTP test client with the database dependency overridden.

    FastAPI's dependency injection lets us swap get_db for a function
    that returns our test session. Every route that calls Depends(get_db)
    gets the rollback-safe test session instead of a real production session.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def product_payload():
    """Sample valid product data reused across tests."""
    return {
        "name": "Test Laptop Pro",
        "description": "A reliable laptop for automated tests",
        "price": 1299.99,
        "category": "electronics",
        "sku": "TEST-ELEC-001",
        "stock_quantity": 10,
    }
