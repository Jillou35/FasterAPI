# RealFastAPI

A production-ready wrapper application framework for FastAPI.

## Features
- Modular Architecture
- Clean Architecture Principles
- Async SQLAlchemy 2.0 Integration
- Generic CRUD
- JWT Authentication & Security

## Installation

```bash
pip install realfastapi
```

## Quick Start

Create a new application:

```python
from realfastapi.core import RealFastAPI, RealFastAPIConfig, DatabaseConfig

config = RealFastAPIConfig(
    title="My App",
    db_config=DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
)

app = RealFastAPI(config)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
```

## Real Example

For a complete, production-ready example including authentication, relationships, and custom endpoints, check out the [Simple App Example](examples/simple_app).

This example demonstrates:
- **Custom Models & Schemas**: Using SQLAlchemy models with relationships (User <-> Items).
- **Authentication**: JWT authentication with protected routes.
- **Custom Endpoints**: Advanced filtering and eager loading to prevent N+1 queries.

## Generic CRUD

RealFastAPI provides a powerful `BaseCRUD` class and `create_crud_router` helper to automatically generate standard CRUD (Create, Read, Update, Delete) endpoints for your SQLAlchemy models.

### Usage

1. **Define Your Schemas**: Create Pydantic models for Create, Update, and Output.
2. **Define Your Model**: Create a SQLAlchemy model.
3. **Initialize BaseCRUD**: Create an instance of `BaseCRUD`.
4. **Create Router**: Use `create_crud_router` to register routes.

```python
from realfastapi.crud.base import BaseCRUD
from realfastapi.crud.routes import create_crud_router

# ... Define Item, ItemCreate, ItemUpdate, ItemOut ...

# Initialize CRUD
crud_item = BaseCRUD(Item, ItemCreate, ItemUpdate, ItemOut)

# Register Routes
create_crud_router(
    crud=crud_item, 
    path="/items", 
    app=app, 
    tags=["Items"]
)
```

This automatically generates the following endpoints:
- `POST /items`: Create a new item.
- `GET /items/{id}`: Get an item by ID.
- `GET /items`: Get multiple items (supports pagination `skip`, `limit`, sorting `sort`, and filtering).
- `PUT /items/{id}`: Update an item.
- `DELETE /items/{id}`: Delete an item.

## Authentication

RealFastAPI includes a built-in JWT authentication system.

### Usage

1. **Configure Auth**: Set up `AuthConfig` in your `RealFastAPIConfig`.
2. **Create Auth Router**: Use `create_auth_router` to generate login endpoints.
3. **Protect Endpoints**: Use `app.get_current_user` dependency.

```python
from realfastapi.auth.routes import create_auth_router
from realfastapi.core import AuthConfig

# 1. Config
auth_config = AuthConfig(
    secret_key="YOUR_SECRET_KEY", 
    token_url="/auth/login"
)
config = RealFastAPIConfig(..., auth_config=auth_config)
app = RealFastAPI(config)

# 2. Auth Router
create_auth_router(
    app=app,
    prefix="/auth",
    crud=crud_user, # Your User CRUD instance
    secret_key="YOUR_SECRET_KEY",
    username_field="username",
    password_field="password",
)

# 3. Protect Endpoint
@app.get("/protected")
async def protected_route(user: str = Depends(app.get_current_user)):
    return {"message": f"Hello {user}"}
```

## Database Migrations

RealFastAPI integrates with **Alembic** for database migrations.

### Usage

1. **Initialize**: Run the CLI command to scaffold migrations.
   ```bash
   python -m realfastapi.cli init-db
   ```
   This creates a `migrations` directory and `alembic.ini`.

2. **Configure**: Edit `migrations/env.py` to import your SQLAlchemy Base.
   ```python
   # migrations/env.py
   from myapp.database import Base # Import your Base
   target_metadata = Base.metadata
   ```

3. **Generate Migration**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

4. **Apply Migration**:
   ```bash
   alembic upgrade head
   ```

## Testing

RealFastAPI provides utilities to make testing easier, including `TestClient` and database overrides.

### Usage

Use `realfastapi.testing.override_get_db` to create an isolated test database. The returned object exposes the `engine` for setup (like creating tables) and behaves as a dependency override.

```python
import pytest
from realfastapi.testing import TestClient, override_get_db
from myapp.main import app
from myapp.database import Base # Import your models

@pytest.mark.asyncio
async def test_create_item():
    # 1. Initialize Test Database
    test_db = override_get_db("sqlite+aiosqlite:///:memory:")
    
    # 2. Create Tables (using exposed engine)
    async with test_db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # 3. Override Dependency
    app.dependency_overrides[app.db.get_db] = test_db
    
    with TestClient(app) as client:
        # Create
        response = client.post("/items", json={"title": "Test Item"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Item"
```

## Requirements

- Python 3.10+
- FastAPI
- SQLAlchemy 2.0+

