from typing import Any, Optional, Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic_settings import BaseSettings
from pydantic import ValidationError

from fasterapi.database.session import Database
from fasterapi.auth.jwt import decode_access_token
from fasterapi.schemas.token import TokenPayload


class DatabaseConfig(BaseSettings):
    url: str


class AuthConfig(BaseSettings):
    secret_key: str
    token_url: str = "/login"
    algorithm: str = "HS256"


class FasterAPIConfig(BaseSettings):
    title: str = "FasterAPI App"
    version: str = "0.1.0"
    db_config: Optional[DatabaseConfig] = None
    auth_config: Optional[AuthConfig] = None


class FasterAPI(FastAPI):
    def __init__(self, config: FasterAPIConfig, **kwargs: Any):
        user_lifespan = kwargs.pop("lifespan", None)

        @asynccontextmanager
        async def default_lifespan(app: FastAPI) -> Any:
            # Handle user defined lifespan if it exists
            if user_lifespan:
                async with user_lifespan(app):
                    yield
            else:
                yield

            # Shutdown: Close DB
            if self.db is not None:
                await self.db.close()

        super().__init__(
            title=config.title,
            version=config.version,
            lifespan=default_lifespan,
            **kwargs,
        )
        self.config = config
        self.db: Optional[Database] = None

        if config.db_config:
            self.db = Database(config.db_config.url)

        self.oauth2_scheme = None
        self.get_current_user = None
        if config.auth_config:
            self.oauth2_scheme = OAuth2PasswordBearer(
                tokenUrl=config.auth_config.token_url
            )

            async def _get_current_user(
                token: Annotated[str, Depends(self.oauth2_scheme)],
            ) -> Any:
                try:
                    if config.auth_config is None:
                        raise RuntimeError("Auth config missing")
                    payload = decode_access_token(token, config.auth_config.secret_key)
                    token_data = TokenPayload(**payload)
                except (ValidationError, Exception) as e:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=str(e),
                    )
                username = token_data.sub
                return username

            self.get_current_user = _get_current_user

        # Register global exception handling
        self.add_exception_handler(Exception, self.global_exception_handler)

    async def global_exception_handler(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),  # In production, might want to hide detailed errors
            },
        )
