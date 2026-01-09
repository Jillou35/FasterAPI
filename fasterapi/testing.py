from typing import AsyncGenerator, Callable, Any
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

__all__ = ["TestClient", "override_get_db"]


def override_get_db(
    test_db_url: str = "sqlite+aiosqlite:///:memory:",
) -> Callable[..., Any]:
    """
    Creates a dependency override for app.db.get_db.

    Usage:
        app.dependency_overrides[app.db.get_db] = override_get_db("sqlite+aiosqlite:///./test.db")
    """
    engine = create_async_engine(test_db_url, echo=False, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    return _get_test_db
