from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import jwt

# Default settings, should be overridden by config
ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any], secret_key: str, expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str, secret_key: str) -> Any:
    return jwt.decode(token, secret_key, algorithms=[ALGORITHM])
