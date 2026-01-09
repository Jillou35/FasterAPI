from typing import Any, Dict, List, Type
from sqlalchemy import Column, asc, desc, inspect
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.sql.elements import BinaryExpression


def parse_filters(
    model: Type[DeclarativeMeta], filters: Dict[str, Any]
) -> List[BinaryExpression[Any]]:
    """
    Parse a dictionary of filters into SQLAlchemy binary expressions.
    Supported format: field__op=value
    Supported ops: eq, ne, gt, lt, gte, lte, like, ilike, in
    """
    expressions = []
    mapper = inspect(model)
    assert mapper is not None

    for key, value in filters.items():
        if value is None:
            continue

        # Default operation is eq
        field_name = key
        op = "eq"

        if "__" in key:
            parts = key.split("__")
            # Check if the last part is a supported operator
            if parts[-1] in {
                "eq",
                "ne",
                "gt",
                "lt",
                "gte",
                "lte",
                "like",
                "ilike",
                "in",
            }:
                op = parts[-1]
                field_name = "__".join(parts[:-1])

        # Check if field exists on model
        if field_name not in mapper.columns:
            continue

        column: Column[Any] = mapper.columns[field_name]

        if op == "eq":
            expressions.append(column == value)
        elif op == "ne":
            expressions.append(column != value)
        elif op == "gt":
            expressions.append(column > value)
        elif op == "lt":
            expressions.append(column < value)
        elif op == "gte":
            expressions.append(column >= value)
        elif op == "lte":
            expressions.append(column <= value)
        elif op == "like":
            expressions.append(column.like(value))
        elif op == "ilike":
            expressions.append(column.ilike(value))
        elif op == "in":
            # Assume value is a list or comma-separated string?
            # For simplicity in query params, it often comes as a list if we use FastAPI generic list handling,
            # but if it comes from **kwargs it might be a single value.
            # strict typing here depends on usage.
            # We'll assume usage passes compatible types (list/tuple).
            if not isinstance(value, (list, tuple)):
                # If it's a string, try splitting by comma?
                # Or just assume the caller handles it.
                # Let's wrap in list if scalar.
                value = [value]
            expressions.append(column.in_(value))

    return expressions


def parse_sort(model: Type[DeclarativeMeta], sort: str) -> List[Any]:
    """
    Parse a sort string into SQLAlchemy order_by clauses.
    Format: "-created_at,name" (comma separated, - for desc, + or none for asc)
    """
    order_by = []

    mapper = inspect(model)
    assert mapper is not None
    fields = sort.split(",")

    for field in fields:
        field = field.strip()
        if not field:
            continue

        direction = "asc"
        if field.startswith("-"):
            direction = "desc"
            field = field[1:]
        elif field.startswith("+"):
            field = field[1:]

        if field in mapper.columns:
            column: Column[Any] = mapper.columns[field]
            if direction == "desc":
                order_by.append(desc(column))
            else:
                order_by.append(asc(column))

    return order_by
