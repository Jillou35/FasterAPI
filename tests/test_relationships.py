import pytest
from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy import ForeignKey
from pydantic import BaseModel
from fastapi import FastAPI, Depends

from realfastapi.core import RealFastAPI, RealFastAPIConfig, DatabaseConfig
from realfastapi.crud.base import BaseCRUD
from realfastapi.database.base import Base


# --- Models ---
class Parent(Base):
    __tablename__ = "parent"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    children: Mapped[List["Child"]] = relationship(back_populates="parent")


class Child(Base):
    __tablename__ = "child"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent.id"))
    parent: Mapped["Parent"] = relationship(back_populates="children")


# --- Schemas ---
class ChildSchema(BaseModel):
    id: int
    name: str


class ParentSchema(BaseModel):
    id: int
    name: str
    children: List[ChildSchema] = []


class ParentCreate(BaseModel):
    name: str


class ChildCreate(BaseModel):
    name: str
    parent_id: int


# --- Test ---
@pytest.mark.asyncio
async def test_relationship_loading(db_instance, db_session):
    # Setup App (minimal)
    db_config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    config = RealFastAPIConfig(db_config=db_config)

    # We use the fixture's engine/session for setup, but the app creates its own.
    # To test BaseCRUD logic directly, we can use the fixture session.

    # Create tables
    async with db_instance.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insert Data
    crud_parent = BaseCRUD(
        Parent,
        create_schema=ParentCreate,
        update_schema=ParentCreate,
        out_schema=ParentCreate,
    )
    crud_child = BaseCRUD(
        Child,
        create_schema=ChildCreate,
        update_schema=ChildCreate,
        out_schema=ChildCreate,
    )

    parent = await crud_parent.create(db_session, obj_in=ParentCreate(name="Parent 1"))
    db_session.expunge(parent)
    await crud_child.create(
        db_session, obj_in=ChildCreate(name="Child A", parent_id=parent.id)
    )
    await crud_child.create(
        db_session, obj_in=ChildCreate(name="Child B", parent_id=parent.id)
    )

    # Test Read with Load Options
    # Without options, accessing .children would fail or trigger IO (if session open)
    # Pydantic validation of ParentSchema triggers access to .children using standard getattr

    # 1. Test read (single) with selectinload
    # Note: We must pass a standard list of options
    loaded_parent = await crud_parent.read(
        db_session, id=parent.id, load_options=[selectinload(Parent.children)]
    )

    assert loaded_parent is not None
    assert len(loaded_parent.children) == 2
    assert loaded_parent.children[0].name in ["Child A", "Child B"]

    # 2. Test read_multi with selectinload
    parents = await crud_parent.read_multi(
        db_session, load_options=[selectinload(Parent.children)]
    )
    assert len(parents) == 1
    assert len(parents[0].children) == 2

    # Verify Pydantic validation works (this effectively tests that the data is loaded)
    pydantic_parent = ParentSchema.model_validate(loaded_parent, from_attributes=True)
    assert len(pydantic_parent.children) == 2

    # Cleanup
    async with db_instance.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
