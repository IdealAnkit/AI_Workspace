"""Reusable FastAPI dependency injection helpers."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.exceptions import ForbiddenException
from app.database.session import get_db as _get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


def get_app_settings() -> Settings:
    """Return the cached application settings instance."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for the duration of the request."""
    async for session in _get_db():
        yield session


DatabaseDep = Annotated[AsyncSession, Depends(get_db)]

# This dependency also declares FastAPI's OpenAPI bearer security scheme.
bearer_scheme = HTTPBearer(
    scheme_name="JWT Bearer Authentication",
    description="Enter an access token returned by /api/v1/auth/login.",
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DatabaseDep,
    settings: SettingsDep,
) -> User:
    """Resolve and validate the active user from a bearer access token."""
    return await AuthService(db, settings).get_current_user(credentials.credentials)


async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Resolve the current user and require the ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException(message="Administrator privileges are required.")
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
CurrentAdminDep = Annotated[User, Depends(get_current_admin)]
