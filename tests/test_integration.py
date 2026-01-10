from tests.conftest import TEST_DATABASE_URL
from realfastapi.auth.jwt import decode_access_token
from realfastapi.auth.routes import create_auth_router
import pytest
from contextlib import asynccontextmanager
from typing import Optional
from httpx import AsyncClient, ASGITransport
from fastapi import Depends

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

from realfastapi.core import RealFastAPI, RealFastAPIConfig, DatabaseConfig, AuthConfig
from realfastapi.crud import BaseCRUD, create_crud_router
from realfastapi.database import Base


# --- Models & Schemas ---
class IntegrationItem(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    password = Column(String)


class IntegrationItemCreate(BaseModel):
    name: str
    password: str


class IntegrationItemUpdate(BaseModel):
    name: str


class IntegrationItemOut(BaseModel):
    id: int
    name: str


class ProtectedItem(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)


class ProtectedItemCreate(BaseModel):
    name: str


class ProtectedItemUpdate(BaseModel):
    name: Optional[str] = None


class ProtectedItemOut(BaseModel):
    id: int
    name: str


crud_item = BaseCRUD(
    model=IntegrationItem,
    create_schema=IntegrationItemCreate,
    update_schema=IntegrationItemUpdate,
    out_schema=IntegrationItemOut,
)

crud_protected = BaseCRUD(
    model=ProtectedItem,
    create_schema=ProtectedItemCreate,
    update_schema=ProtectedItemUpdate,
    out_schema=ProtectedItemOut,
)

# --- Test Setup ---


@pytest.fixture
async def app_instance():
    # Define lifespan to create tables
    @asynccontextmanager
    async def lifespan(app: RealFastAPI):
        if app.db:
            async with app.db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        yield
        # Cleanup is handled by RealFastAPI default lifespan + engine dispose

    db_config = DatabaseConfig(url=TEST_DATABASE_URL)
    auth_config = AuthConfig(secret_key="TEST_KEY", token_url="/login")
    config = RealFastAPIConfig(
        title="Integration Test App", db_config=db_config, auth_config=auth_config
    )
    # Pass our lifespan. RealFastAPI core wrapper handles calling it.
    app = RealFastAPI(config, lifespan=lifespan)

    create_crud_router(
        crud=crud_item, path="/items", app=app, password_field="password"
    )

    create_auth_router(
        crud=crud_item,
        app=app,
        secret_key="TEST_KEY",
        username_field="name",
        password_field="password",
    )

    # Protected Route Setup
    # No manual scheme needed!

    create_crud_router(
        crud=crud_protected,
        path="/protected",
        app=app,
        dependencies=[Depends(app.get_current_user)],
    )

    # Manually trigger lifespan
    # This ensures that our lifespan function (and thus table creation) is called
    async with app.router.lifespan_context(app):
        yield app


@pytest.mark.asyncio
async def test_integration_flow(app_instance: RealFastAPI):
    # Pass transport to AsyncClient with app to handle requests against the in-memory app
    async with AsyncClient(
        transport=ASGITransport(app=app_instance), base_url="http://test"
    ) as ac:
        # 1. Create
        response = await ac.post(
            "/items", json={"name": "Integration Test", "password": "password"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Integration Test"
        data_id = data["id"]

        response_2 = await ac.post(
            "/items", json={"name": "Integration Test 2", "password": "password_2"}
        )
        assert response_2.status_code == 200
        data_2 = response_2.json()
        assert data_2["name"] == "Integration Test 2"
        data_id_2 = data_2["id"]

        # 2. Read
        response_get = await ac.get(f"/items/{data_id}")
        assert response_get.status_code == 200
        data_get = response_get.json()
        assert data_get["name"] == "Integration Test"
        assert data_get["id"] == data_id

        # 3. Read All
        response_get_all = await ac.get("/items")
        assert response_get_all.status_code == 200
        data_get_all = response_get_all.json()
        assert len(data_get_all) == 2
        assert data_get_all[0]["name"] == "Integration Test"
        assert data_get_all[0]["id"] == data_id
        assert data_get_all[1]["name"] == "Integration Test 2"
        assert data_get_all[1]["id"] == data_id_2

        response_get_filtered = await ac.get("/items?skip=0&limit=1")
        assert response_get_filtered.status_code == 200
        data_get_filtered = response_get_filtered.json()
        assert len(data_get_filtered) == 1
        assert data_get_filtered[0]["name"] == "Integration Test"
        assert data_get_filtered[0]["id"] == data_id

        response_get_filtered_2 = await ac.get("/items?skip=1&limit=1")
        assert response_get_filtered_2.status_code == 200
        data_get_filtered_2 = response_get_filtered_2.json()
        assert len(data_get_filtered_2) == 1
        assert data_get_filtered_2[0]["name"] == "Integration Test 2"
        assert data_get_filtered_2[0]["id"] == data_id_2

        response_get_filtered_3 = await ac.get("/items?name=Integration%20Test")
        assert response_get_filtered_3.status_code == 200
        data_get_filtered_3 = response_get_filtered_3.json()
        assert len(data_get_filtered_3) == 1
        assert data_get_filtered_3[0]["name"] == "Integration Test"
        assert data_get_filtered_3[0]["id"] == data_id

        # 4. Update
        response_update = await ac.put(
            f"/items/{data_id}", json={"name": "Integration Test Updated"}
        )
        assert response_update.status_code == 200
        data_update = response_update.json()
        assert data_update["name"] == "Integration Test Updated"
        assert data_update["id"] == data_id

        # 5. Delete
        response_delete = await ac.delete(f"/items/{data_id}")
        assert response_delete.status_code == 200
        data_delete = response_delete.json()
        assert data_delete["name"] == "Integration Test Updated"
        assert data_delete["id"] == data_id

        # 6. Read / Not found
        response_get_all = await ac.get(f"/items/{data_id}")
        assert response_get_all.status_code == 404
        data_get_all = response_get_all.json()
        assert data_get_all["detail"] == "Item not found"

        # 7. Update / Not found
        response_get_all = await ac.put(
            f"/items/{data_id}", json={"name": "Integration Test Updated"}
        )
        assert response_get_all.status_code == 404
        data_get_all = response_get_all.json()
        assert data_get_all["detail"] == "Item not found"

        # 8. Delete / Not found
        response_get_all = await ac.delete(f"/items/{data_id}")
        assert response_get_all.status_code == 404
        data_get_all = response_get_all.json()
        assert data_get_all["detail"] == "Item not found"

        # 9. Bad request
        response_get_all = await ac.get("/items?wrong_param=1")
        assert response_get_all.status_code == 400
        data_get_all = response_get_all.json()
        assert data_get_all["detail"] == "Invalid query parameter: wrong_param"

        # 10. Login
        response_login = await ac.post(
            "/login", data={"username": "Integration Test 2", "password": "password_2"}
        )
        assert response_login.status_code == 200
        data_login = response_login.json()
        assert data_login["access_token"]
        decoded_access_token = decode_access_token(
            data_login["access_token"], "TEST_KEY"
        )
        assert decoded_access_token["sub"] == "Integration Test 2"

        # Wrong password
        response_login = await ac.post(
            "/login",
            data={"username": "Integration Test 2", "password": "wrong_password"},
        )
        assert response_login.status_code == 401
        data_wrong_login = response_login.json()
        assert data_wrong_login["detail"] == "Incorrect username or password"

        # Wrong username
        response_login = await ac.post(
            "/login", data={"username": "wrong_username", "password": "password_2"}
        )
        assert response_login.status_code == 401
        data_wrong_login = response_login.json()
        assert data_wrong_login["detail"] == "Incorrect username or password"

        # Logout
        response_logout = await ac.post("/logout")
        assert response_logout.status_code == 200
        data_logout = response_logout.json()
        assert data_logout["message"] == "Successfully logged out"

        # 11. Protected route
        # Fail without token
        response_protected_fail = await ac.get("/protected")
        assert response_protected_fail.status_code == 401

        # Success with token
        response_protected = await ac.post(
            "/protected",
            json={"name": "Protected Data"},
            headers={"Authorization": f"Bearer {data_login['access_token']}"},
        )
        assert response_protected.status_code == 200
        data_protected = response_protected.json()
        assert data_protected["name"] == "Protected Data"

        # 12. Advanced Filtering
        # Create items for filtering
        await ac.post("/items", json={"name": "Alice", "password": "pass"})  # id 3
        await ac.post("/items", json={"name": "Bob", "password": "pass"})  # id 4
        await ac.post("/items", json={"name": "Charlie", "password": "pass"})  # id 5

        # ilike
        response_ilike = await ac.get("/items?name__ilike=%li%")
        assert response_ilike.status_code == 200
        data_ilike = response_ilike.json()
        names_ilike = [item["name"] for item in data_ilike]
        assert "Alice" in names_ilike
        assert "Charlie" in names_ilike
        assert "Bob" not in names_ilike

        # gt (id > 3)
        response_gt = await ac.get("/items?id__gt=3")
        assert response_gt.status_code == 200
        data_gt = response_gt.json()
        ids_gt = [item["id"] for item in data_gt]
        assert 4 in ids_gt
        assert 5 in ids_gt
        assert 3 not in ids_gt

        # Sort (descending name)
        response_sort = await ac.get("/items?sort=-name")
        assert response_sort.status_code == 200
        data_sort = response_sort.json()
        sorted_names = [item["name"] for item in data_sort]
        # Should be Integration Test 2, Integration Test 3 (from previous steps), Charlie, Bob, Alice...
        # Just check that it's sorted roughly
        assert sorted_names == sorted(sorted_names, reverse=True)

        # 13. Protected / Not found
        # Ensure we cover the 404 branch for the protected router instance too
        response_protected_nf = await ac.get(
            "/protected/99999",
            headers={"Authorization": f"Bearer {data_login['access_token']}"},
        )
        assert response_protected_nf.status_code == 404
        assert response_protected_nf.json()["detail"] == "Item not found"
