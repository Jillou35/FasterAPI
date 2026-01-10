from typing import AsyncGenerator, Callable, Any
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from sqlalchemy.pool import StaticPool

__all__ = ["TestClient", "override_get_db", "TestDatabase"]


class TestDatabase:
    def __init__(self, test_db_url: str = "sqlite+aiosqlite:///:memory:"):
        connect_args = {}
        poolclass = None

        if "sqlite" in test_db_url and ":memory:" in test_db_url:
            connect_args = {"check_same_thread": False}
            poolclass = StaticPool

        self.engine = create_async_engine(
            test_db_url,
            echo=False,
            future=True,
            connect_args=connect_args,
            poolclass=poolclass,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def __call__(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()


def override_get_db(
    test_db_url: str = "sqlite+aiosqlite:///:memory:",
) -> TestDatabase:
    """
    Creates a dependency override for app.db.get_db.
    Returns a callable TestDatabase object that also exposes `.engine`.

    Usage:
        test_db = override_get_db("sqlite+aiosqlite:///:memory:")
        app.dependency_overrides[app.db.get_db] = test_db
        # Access engine for lifespan/setup:
        async with test_db.engine.begin() as conn: ...
    """
    return TestDatabase(test_db_url)
