from fasterapi.schemas.user import UserCreate, User
from fasterapi.schemas.token import TokenPayload


def test_user_create_schema():
    email = "test@example.com"
    password = "secret_password"
    user_in = UserCreate(email=email, password=password)
    assert user_in.email == email
    assert user_in.password == password


def test_user_schema_attributes():
    # User (response) schema should not have password field usually,
    # but here we just check it matches the definition
    user = User(email="test@example.com", id=1)
    assert user.email == "test@example.com"
    assert user.id == 1
    # Check inheritance of default values
    assert user.is_active is True
    assert user.is_superuser is False


def test_token_payload_schema():
    sub = "user_id_123"
    payload = TokenPayload(sub=sub)
    assert payload.sub == sub
