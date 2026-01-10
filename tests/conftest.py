from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from realfastapi.database.base import Base
from realfastapi.testing import override_get_db

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def db_instance():
    # Use the library's override mechanism which now handles engine/session creation
    # and optimizes for in-memory SQLite.
    test_db = override_get_db(TEST_DATABASE_URL)
    yield test_db
    await test_db.engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_instance) -> AsyncGenerator[AsyncSession, None]:
    # Create tables
    async with db_instance.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Use the session generator from the TestDatabase instance
    # We need a single session for the test, so we iterate once.
    async for session in db_instance():
        yield session
        break

    # Drop tables
    async with db_instance.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
