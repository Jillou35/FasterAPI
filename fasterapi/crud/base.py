from typing import Any, Dict, Type, Optional, TypeVar, Union, Sequence

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType", bound=Any)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
OutSchemaType = TypeVar("OutSchemaType", bound=BaseModel)


class BaseCRUD:
    def __init__(
        self,
        model: Type[ModelType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        out_schema: Type[OutSchemaType],
    ):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `create_schema`: A Pydantic model class for creation
        * `update_schema`: A Pydantic model class for updates
        * `out_schema`: A Pydantic model class for output
        """
        self.model: Type[ModelType] = model
        self.create_schema: Type[CreateSchemaType] = create_schema
        self.update_schema: Type[UpdateSchemaType] = update_schema
        self.out_schema: Type[OutSchemaType] = out_schema

    async def read(
        self, db: AsyncSession, id: Any, load_options: Optional[Sequence[Any]] = None
    ) -> Optional[ModelType]:
        """
        Get a single record by ID.
        """
        if load_options:
            stmt = (
                select(self.model)
                .where(getattr(self.model, "id") == id)
                .options(*load_options)
            )
            result = await db.execute(stmt)
            return result.scalars().first()
        return await db.get(self.model, id)

    async def read_multi(
        self,
        db: AsyncSession,
        *,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        load_options: Optional[Sequence[Any]] = None,
        **kwargs: Any,
    ) -> Sequence[ModelType]:
        """
        Get multiple records with pagination, sorting, and filtering.
        """
        from fasterapi.crud.filters import parse_filters, parse_sort

        query = select(self.model)

        if load_options:
            query = query.options(*load_options)

        # Merge kwargs into filters
        final_filters = filters or {}
        if kwargs:
            final_filters.update(kwargs)

        # Apply filters
        if final_filters:
            criteria = parse_filters(self.model, final_filters)
            if criteria:
                query = query.where(and_(*criteria))

        # Apply sorting
        if sort:
            order_by = parse_sort(self.model, sort)
            if order_by:
                query = query.order_by(*order_by)

        if skip is not None:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType
    ) -> Optional[ModelType]:
        """
        Create a new record.
        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj: Optional[ModelType] = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> Optional[ModelType]:
        """
        Update an existing record.
        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        Delete a record by ID.
        """
        obj = await db.get(self.model, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
