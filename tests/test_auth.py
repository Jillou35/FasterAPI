from datetime import timedelta

import pytest

from realfastapi.auth import security
from realfastapi.auth.jwt import create_access_token, decode_access_token


def test_hash_password():
    password = "secret_password"
    hashed = security.get_password_hash(password)
    assert hashed != password
    assert security.verify_password(password, hashed)
    assert not security.verify_password("wrong_password", hashed)


def test_jwt_create_and_decode():
    secret_key = "test_secret"
    data = "user@example.com"

    # Test Create
    token = create_access_token(subject=data, secret_key=secret_key)
    assert isinstance(token, str)

    # Test Decode
    decoded = decode_access_token(token, secret_key)
    assert decoded["sub"] == data
    assert "exp" in decoded


def test_jwt_expiration():
    secret_key = "test_secret"
    data = "expired@example.com"

    # Create token that expires immediately (-1 second)
    expires = timedelta(seconds=-1)
    token = create_access_token(
        subject=data, secret_key=secret_key, expires_delta=expires
    )

    # Decoding should raise generic Exception (or specific jwt.ExpiredSignatureError)
    # Since our decode wrapper doesn't catch exceptions, we expect the library to raise
    with pytest.raises(Exception):
        decode_access_token(token, secret_key)


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    from realfastapi.core import RealFastAPI, RealFastAPIConfig, AuthConfig
    from realfastapi.schemas.token import TokenPayload

    secret_key = "test_secret"
    auth_config = AuthConfig(secret_key=secret_key)
    config = RealFastAPIConfig(title="Test", auth_config=auth_config)
    app = RealFastAPI(config)

    email = "test@example.com"
    token = create_access_token(subject=email, secret_key=secret_key)

    # We call the dependency directly
    username = await app.get_current_user(token=token)
    assert isinstance(username, str)
    assert username == email


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    from realfastapi.core import RealFastAPI, RealFastAPIConfig, AuthConfig
    from fastapi import HTTPException

    secret_key = "test_secret"
    auth_config = AuthConfig(secret_key=secret_key)
    config = RealFastAPIConfig(title="Test", auth_config=auth_config)
    app = RealFastAPI(config)

    with pytest.raises(HTTPException) as exc:
        await app.get_current_user(token="invalid_token")

    assert exc.value.status_code == 403
