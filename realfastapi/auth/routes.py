from typing import Any
from enum import Enum
from realfastapi.database.session import Database
from typing import Sequence
from typing import List
from typing import Optional
from realfastapi.core import RealFastAPI
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from realfastapi.auth.jwt import create_access_token
from realfastapi.auth.security import verify_password
from realfastapi.crud.base import BaseCRUD, ModelType
from realfastapi.schemas.token import Token


def create_auth_router(
    crud: BaseCRUD,
    app: RealFastAPI,
    secret_key: str,
    username_field: str = "email",  # default field to check for username
    password_field: str = "hashed_password",  # default field to check for hashed password,
    tags: Optional[List[str | Enum]] = None,
    prefix: str = "",
) -> None:
    router = APIRouter(tags=tags, prefix=prefix)

    if app.db is None:
        raise ValueError("Database not initialized")
    else:
        app_db: Database = app.db

    @router.post("/login", response_model=Token)
    async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(app_db.get_db),
    ) -> Token:
        # 1. Fetch user by username field
        # mypy check for kwargs unpacking
        query_filters = {username_field: form_data.username}
        user_list: Sequence[Any] = await crud.read_multi(db, filters=query_filters)
        if len(user_list) != 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = user_list[0]
        # 2. Verify password
        user_password = getattr(user, password_field, None)
        assert isinstance(user_password, str)
        if not verify_password(form_data.password, user_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        subject = getattr(user, username_field)
        access_token = create_access_token(subject=str(subject), secret_key=secret_key)

        token = Token(access_token=access_token, token_type="bearer")

        return token

    @router.post("/logout")
    async def logout() -> Dict[str, str]:
        # Stateless JWT logout is purely client-side action (discard token).
        # We provide this endpoint as a convenience/acknowledgement.
        return {"message": "Successfully logged out"}

    app.include_router(router)
