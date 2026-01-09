from typing import Sequence
from typing_extensions import TypeAlias
from fasterapi.crud.base import (
    ModelType,
    OutSchemaType,
    CreateSchemaType,
    UpdateSchemaType,
)
from fasterapi.database.session import Database
from enum import Enum
from fasterapi.auth.security import get_password_hash
from fasterapi.core import FasterAPI
from typing import List, Optional, Any, Type

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect

from fasterapi.crud.base import BaseCRUD


def create_crud_router(
    crud: BaseCRUD,
    path: str,
    app: FasterAPI,
    password_field: Optional[str] = None,
    dependencies: Optional[List[Any]] = None,
    tags: Optional[List[str | Enum]] = None,
) -> None:
    router = APIRouter(dependencies=dependencies, tags=tags, prefix=path)
    if app.db is None:
        raise ValueError("Database not initialized")
    else:
        app_db: Database = app.db

    create_schema: TypeAlias = crud.create_schema  # type: ignore
    update_schema: TypeAlias = crud.update_schema  # type: ignore
    out_schema: TypeAlias = crud.out_schema  # type: ignore
    model: TypeAlias = crud.model  # type: ignore

    # Dynamic schemas are runtime values, not static types.
    # Mypy cannot type check against crud.model etc.
    # We rely on FastAPI runtime validation (decorator) and use Any for static analysis.

    @router.post("", response_model=out_schema)
    async def create(
        item_in: create_schema, db: AsyncSession = Depends(app_db.get_db)
    ) -> model:
        if password_field:
            item_in_data = item_in.model_dump()
            item_in_data[password_field] = get_password_hash(
                item_in_data[password_field]
            )
            # Reconstruct using the dynamic schema
            item_in = crud.create_schema(**item_in_data)
        return await crud.create(db, obj_in=item_in)

    @router.get("/{id}", response_model=out_schema)
    async def read(id: int, db: AsyncSession = Depends(app_db.get_db)) -> model:
        item: Optional[model] = await crud.read(db, id=id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return item

    @router.get("", response_model=List[out_schema])
    async def read_multi(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[str] = None,
        db: AsyncSession = Depends(app_db.get_db),
    ) -> Sequence[model]:
        # Strict check for unknown parameters
        # Allow skip, limit, sort, and fields (including field__op)
        allowed_base = {"skip", "limit", "sort"}

        # Allow fields from the model itself
        mapper = inspect(model)
        allowed_base.update(mapper.columns.keys())

        # Also allow fields from update_schema if any (though usually model covers it)
        if update_schema:
            allowed_base |= update_schema.model_fields.keys()

        filters = {}
        for param, value in request.query_params.items():
            if param in {"skip", "limit", "sort"}:
                continue

            # Check base param name
            base_param = param.split("__")[0]
            if base_param not in allowed_base:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid query parameter: {param}",
                )

            filters[param] = value

        return await crud.read_multi(
            db, skip=skip, limit=limit, sort=sort, filters=filters
        )

    @router.put("/{id}", response_model=out_schema)
    async def update(
        id: int, item_in: update_schema, db: AsyncSession = Depends(app_db.get_db)
    ) -> model:
        item: Optional[model] = await crud.read(db, id=id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return await crud.update(db, db_obj=item, obj_in=item_in)

    @router.delete("/{id}", response_model=out_schema)
    async def delete(id: int, db: AsyncSession = Depends(app_db.get_db)) -> model:
        item: Optional[model] = await crud.read(db, id=id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return await crud.delete(db, id=id)

    app.include_router(router)
