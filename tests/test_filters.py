import pytest
from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from fasterapi.core import FasterAPIConfig, DatabaseConfig
from fasterapi.crud.filters import parse_filters
from fasterapi.database.base import Base
from sqlalchemy import select, and_, inspect


# Reuse Base from database.base
class FilterItem(Base):
    __tablename__ = "filter_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    age: Mapped[int] = mapped_column()


# We can test parse_filters directly unit-test style to be faster/more robust
# without needing full DB roundtrip for every operator, but full integration is good too.
# Let's do Unit Test of parse_filters first, then maybe one integration check.


def test_parse_filters_unit():
    # Helper to check SQL string roughly
    filters = {
        "name__eq": "Alice",
        "age__gt": 18,
        "age__lt": 30,
        "name__ne": "Bob",
        "name__in": ["Alice", "Charlie"],
    }

    criteria = parse_filters(FilterItem, filters)
    assert len(criteria) == 5

    # We can inspect the expressions
    # This is slightly implementation detail dependent but ensures logic handles keys

    # Just verifying no crash and correct count.
    # To verify SQL generation we need a compiled statement.
    stmt = select(FilterItem).where(and_(*criteria))
    compiled = str(stmt)
    assert (
        "filter_item.name = :name_1" in compiled
        or "filter_item.name = :name_1" in compiled
    )
    assert "filter_item.age > :age_1" in compiled or "filter_item.age >" in compiled
    # Exact caching of bind params makes string check valid-ish but fragile.

    # Better: check operators
    c0 = criteria[0]
    # Inspecting binary expressions is efficient.


@pytest.mark.asyncio
async def test_filters_integration(db_engine, db_session):
    # Setup
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from fasterapi.crud.base import BaseCRUD

    class ItemCreate(BaseModel):
        name: str
        age: int

    crud = BaseCRUD(
        FilterItem,
        create_schema=ItemCreate,
        update_schema=ItemCreate,
        out_schema=ItemCreate,
    )

    # Insert Data
    await crud.create(db_session, obj_in=ItemCreate(name="Alice", age=25))
    await crud.create(db_session, obj_in=ItemCreate(name="Bob", age=30))
    await crud.create(db_session, obj_in=ItemCreate(name="Charlie", age=35))
    await crud.create(db_session, obj_in=ItemCreate(name="David", age=20))

    # 1. Test NE (Not Equal)
    res_ne = await crud.read_multi(db_session, filters={"name__ne": "Alice"})
    assert len(res_ne) == 3
    names = [x.name for x in res_ne]
    assert "Alice" not in names

    # 2. Test LT (Less Than)
    res_lt = await crud.read_multi(db_session, filters={"age__lt": 25})
    assert len(res_lt) == 1
    assert res_lt[0].name == "David"

    # 3. Test IN
    res_in = await crud.read_multi(
        db_session, filters={"name__in": ["Alice", "Charlie"]}
    )
    assert len(res_in) == 2
    names_in = [x.name for x in res_in]
    assert "Alice" in names_in
    assert "Charlie" in names_in

    # 3. Test IN
    res_in = await crud.read_multi(db_session, filters={"name__in": "Alice"})
    assert len(res_in) == 1
    names_in = [x.name for x in res_in]
    assert "Alice" in names_in

    # 4. Test GTE/LTE
    res_range = await crud.read_multi(
        db_session, filters={"age__gte": 25, "age__lte": 30}
    )
    assert len(res_range) == 2
    names_range = [x.name for x in res_range]
    assert "Alice" in names_range
    assert "Bob" in names_range
    assert "David" not in names_range

    # 5. Test LIKE
    res_like = await crud.read_multi(db_session, filters={"name__like": "%li%"})
    assert len(res_like) == 2
    names_like = [x.name for x in res_like]
    assert "Alice" in names_like
    assert "Charlie" in names_like
    assert "Bob" not in names_like

    # 6. Test ILIKE
    res_ilike = await crud.read_multi(db_session, filters={"name__ilike": "%li%"})
    assert len(res_ilike) == 2
    names_ilike = [x.name for x in res_ilike]
    assert "Alice" in names_ilike
    assert "Charlie" in names_ilike
    assert "Bob" not in names_ilike

    # 7. Test unknown field
    res_unknown = await crud.read_multi(db_session, filters={"name__unknown": "Alice"})
    assert len(res_unknown) == 4

    # 8. Test no value
    res_no_value = await crud.read_multi(db_session, filters={"name__eq": None})
    assert len(res_no_value) == 4

    # 9. Test sort
    res_sort = await crud.read_multi(db_session, sort="age")
    assert len(res_sort) == 4
    names_sort = [x.name for x in res_sort]
    assert names_sort == ["David", "Alice", "Bob", "Charlie"]

    # 10. Test sort desc
    res_sort_desc = await crud.read_multi(db_session, sort="-age")
    assert len(res_sort_desc) == 4
    names_sort_desc = [x.name for x in res_sort_desc]
    assert names_sort_desc == ["Charlie", "Bob", "Alice", "David"]

    # 11. Test sort multiple fields
    res_sort_multi = await crud.read_multi(db_session, sort="+name,-age")
    assert len(res_sort_multi) == 4
    names_sort_multi = [x.name for x in res_sort_multi]
    assert names_sort_multi == ["Alice", "Bob", "Charlie", "David"]

    # 12. Test sort no value
    res_sort_multi_desc = await crud.read_multi(db_session, sort=",")
    assert len(res_sort_multi_desc) == 4
    names_sort_multi_desc = [x.name for x in res_sort_multi_desc]
    assert names_sort_multi_desc == ["Alice", "Bob", "Charlie", "David"]

    # Cleanup
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
