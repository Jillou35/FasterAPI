from tests.conftest import TEST_DATABASE_URL
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from fastapi import Request

from fasterapi.core import FasterAPI, FasterAPIConfig, DatabaseConfig


def test_config_defaults():
    config = FasterAPIConfig()
    assert config.title == "FasterAPI App"
    assert config.version == "0.1.0"
    assert config.db_config is None


def test_init_without_db():
    config = FasterAPIConfig(title="My App", version="1.0")
    app = FasterAPI(config)

    assert app.title == "My App"
    assert app.version == "1.0"
    assert app.db is None


def test_init_with_db():
    db_config = DatabaseConfig(url=TEST_DATABASE_URL)
    config = FasterAPIConfig(db_config=db_config)
    app = FasterAPI(config)

    assert app.db is not None
    assert app.db.engine is not None  # Basic check that Database was init


@pytest.mark.asyncio
async def test_lifespan_closes_db():
    # Mock Database to verify close is called
    with patch("fasterapi.core.Database") as MockDatabase:
        mock_db_instance = AsyncMock()
        MockDatabase.return_value = mock_db_instance

        db_config = DatabaseConfig(url="sqlite:///:memory:")
        config = FasterAPIConfig(db_config=db_config)
        app = FasterAPI(config)

        # Manually trigger lifespan
        # app.router.lifespan_context is the wrapper around the lifespan function
        async with app.router.lifespan_context(app):
            pass

        mock_db_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_calls_user_lifespan():
    mock_lifespan = AsyncMock()

    @asynccontextmanager
    async def user_lifespan(app):
        await mock_lifespan(app)
        yield

    config = FasterAPIConfig()
    app = FasterAPI(config, lifespan=user_lifespan)

    async with app.router.lifespan_context(app):
        pass

    mock_lifespan.assert_called_once_with(app)


@pytest.mark.asyncio
async def test_global_exception_handler():
    config = FasterAPIConfig()
    app = FasterAPI(config)

    request = MagicMock(spec=Request)
    exc = ValueError("Something went wrong")

    response = await app.global_exception_handler(request, exc)

    assert response.status_code == 500
    import json

    body = json.loads(response.body)
    assert body["error"] == "Internal Server Error"
    assert body["detail"] == "Something went wrong"
