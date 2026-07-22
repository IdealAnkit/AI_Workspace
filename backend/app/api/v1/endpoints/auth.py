"""HTTP endpoints for authentication and the initial two-role authorization model."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, DatabaseDep, SettingsDep
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from app.schemas.responses import SuccessResponse
from app.services.auth_service import AuthService
from app.utils.responses import created, ok

router = APIRouter()


@router.post("/register", response_model=SuccessResponse[AuthResponse], status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DatabaseDep, settings: SettingsDep) -> SuccessResponse[AuthResponse]:
    """Create a user account and issue its first access and refresh tokens."""
    result = await AuthService(db, settings).register(payload)
    return created(data=result, message="Registration successful.")


@router.post("/login", response_model=SuccessResponse[AuthResponse])
async def login(payload: LoginRequest, db: DatabaseDep, settings: SettingsDep) -> SuccessResponse[AuthResponse]:
    """Verify credentials and issue a new access/refresh token pair."""
    result = await AuthService(db, settings).login(payload)
    return ok(data=result, message="Login successful.")


@router.post("/refresh", response_model=SuccessResponse[TokenPairResponse])
async def refresh(payload: RefreshRequest, db: DatabaseDep, settings: SettingsDep) -> SuccessResponse[TokenPairResponse]:
    """Rotate a valid refresh token and return a new token pair."""
    result = await AuthService(db, settings).refresh(payload.refresh_token)
    return ok(data=result, message="Tokens refreshed.")


@router.post("/logout", response_model=SuccessResponse[None])
async def logout(payload: LogoutRequest, db: DatabaseDep, settings: SettingsDep) -> SuccessResponse[None]:
    """Revoke the supplied refresh token's server-side session."""
    await AuthService(db, settings).logout(payload.refresh_token)
    return ok(message="Logout successful.")


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(current_user: CurrentUserDep) -> SuccessResponse[UserResponse]:
    """Return the authenticated user's safe public account data."""
    return ok(data=UserResponse.model_validate(current_user), message="Current user retrieved.")
