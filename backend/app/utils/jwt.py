"""JWT creation and validation helpers for access and refresh tokens."""

import hashlib
import uuid
from datetime import timedelta
from typing import Any

from jose import JWTError, jwt

from app.config.settings import Settings
from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from app.utils.datetime import utcnow


def create_access_token(*, subject: str, role: str, settings: Settings) -> str:
    """Create a signed short-lived access token."""
    now = utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, subject: str, settings: Settings) -> tuple[str, str, Any]:
    """Create a signed refresh token and return it with its JTI and expiry."""
    now = utcnow()
    jti = str(uuid.uuid4())
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "type": REFRESH_TOKEN_TYPE,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verify a token signature and return its claims, raising JWTError if invalid."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def hash_token_identifier(token_identifier: str) -> str:
    """Store only a non-reversible representation of refresh-token JTIs."""
    return hashlib.sha256(token_identifier.encode("utf-8")).hexdigest()


__all__ = [
    "JWTError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_token_identifier",
]
