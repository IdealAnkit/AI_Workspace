"""Password hashing helpers. Passwords are never persisted in plaintext."""

from passlib.context import CryptContext

_password_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True
)


def hash_password(password: str) -> str:
    """Return a bcrypt hash for a plaintext password."""
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored bcrypt hash."""
    return _password_context.verify(password, password_hash)
