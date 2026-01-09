from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fasterapi.database.base import Base

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def db_engine():
    # Create engine per function to ensure loop compatibility
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    # Create tables
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    TestingSessionLocal = sessionmaker(
        class_=AsyncSession, autocommit=False, autoflush=False, bind=db_engine
    )

    async with TestingSessionLocal() as session:
        yield session

    # Drop tables (though engine dispose might handle memory db cleanup, this is explicit)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
