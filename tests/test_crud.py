from typing import Optional

import pytest
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from realfastapi.crud.base import BaseCRUD
from realfastapi.database.base import Base


# --- Test Models & Schemas ---
class Item(Base):
    __tablename__ = "test_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)


class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class ItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None


crud_item = BaseCRUD(
    model=Item, create_schema=ItemCreate, update_schema=ItemUpdate, out_schema=ItemOut
)


# --- Tests ---
@pytest.mark.asyncio
async def test_create_item(db_session: AsyncSession):
    item_in = ItemCreate(title="Test Item", description="A test item")
    item = await crud_item.create(db_session, obj_in=item_in)

    assert item.title == "Test Item"
    assert item.description == "A test item"
    assert hasattr(item, "id")


@pytest.mark.asyncio
async def test_read_item(db_session: AsyncSession):
    item_in = ItemCreate(title="Get Me")
    item = await crud_item.create(db_session, obj_in=item_in)

    stored_item = await crud_item.read(db_session, id=item.id)
    assert stored_item
    assert stored_item.id == item.id
    assert stored_item.title == item.title


@pytest.mark.asyncio
async def test_update_item(db_session: AsyncSession):
    item_in = ItemCreate(title="Original")
    item = await crud_item.create(db_session, obj_in=item_in)

    update_data = ItemUpdate(title="Updated")
    updated_item = await crud_item.update(db_session, db_obj=item, obj_in=update_data)

    assert updated_item.id == item.id
    assert updated_item.title == "Updated"


@pytest.mark.asyncio
async def test_delete_item(db_session: AsyncSession):
    item_in = ItemCreate(title="To Delete")
    item = await crud_item.create(db_session, obj_in=item_in)

    removed_item = await crud_item.delete(db_session, id=item.id)
    assert removed_item
    assert removed_item.id == item.id

    stmt = await crud_item.read(db_session, id=item.id)
    assert stmt is None


@pytest.mark.asyncio
async def test_read_multi_items(db_session: AsyncSession):
    for i in range(15):
        item_in = ItemCreate(title=f"Item {i}", description=f"Description {i}")
        await crud_item.create(db_session, obj_in=item_in)

    items = await crud_item.read_multi(db_session, skip=0, limit=10)
    assert len(items) == 10

    items_skip = await crud_item.read_multi(db_session, skip=10, limit=10)
    assert len(items_skip) == 5


@pytest.mark.asyncio
async def test_update_item_with_dict(db_session: AsyncSession):
    item_in = ItemCreate(title="Original", description="Desc")
    item = await crud_item.create(db_session, obj_in=item_in)

    update_data = {"title": "Updated Dict"}
    updated_item = await crud_item.update(db_session, db_obj=item, obj_in=update_data)

    assert updated_item.title == "Updated Dict"
    assert updated_item.description == "Desc"
