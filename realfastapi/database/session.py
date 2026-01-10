from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Default to SQLite for testing/defaults if not configured,
# but the goal is to allow injection.
# For now, we provide the factory logic.


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(database_url, echo=False, future=True)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def close(self) -> None:
        await self.engine.dispose()
