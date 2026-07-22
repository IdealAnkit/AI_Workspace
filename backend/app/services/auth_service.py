"""Authentication business logic, kept independent from HTTP route handling."""

import uuid

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from app.core.exceptions import ConflictException, UnauthorizedException
from app.models.user import RefreshSession, User, UserRole
from app.repositories.user_repository import RefreshSessionRepository, UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenPairResponse, UserResponse
from app.utils.datetime import utcnow
from app.utils.jwt import create_access_token, create_refresh_token, decode_token, hash_token_identifier
from app.utils.password import hash_password, verify_password


class AuthService:
    """Coordinates account creation, credential checks, and token lifecycle."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.user_repository = UserRepository(session)
        self.refresh_session_repository = RefreshSessionRepository(session)
        self.settings = settings

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        """Register a standard user after enforcing unique account identifiers."""
        if await self.user_repository.get_by_email(str(payload.email)):
            raise ConflictException(message="An account with this email already exists.")
        if await self.user_repository.get_by_username(payload.username):
            raise ConflictException(message="This username is already in use.")

        user = await self.user_repository.create(
            User(
                email=str(payload.email), username=payload.username, full_name=payload.full_name,
                password_hash=hash_password(payload.password), role=UserRole.USER,
            )
        )
        return await self._build_auth_response(user)

    async def login(self, payload: LoginRequest) -> AuthResponse:
        """Authenticate active user credentials and create a fresh token pair."""
        user = await self.user_repository.get_by_email(str(payload.email))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedException(message="Incorrect email or password.")
        if not user.is_active:
            raise UnauthorizedException(message="This account is inactive.")
        return await self._build_auth_response(user)

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        """Rotate an active refresh token, invalidating the token presented."""
        claims = self._decode_expected_token(refresh_token, REFRESH_TOKEN_TYPE)
        token_identifier, subject = claims.get("jti"), claims.get("sub")
        if not isinstance(token_identifier, str) or not isinstance(subject, str):
            raise UnauthorizedException(message="Invalid refresh token.")
        refresh_session = await self.refresh_session_repository.get_active_by_token_hash(
            hash_token_identifier(token_identifier)
        )
        if refresh_session is None or refresh_session.expires_at <= utcnow():
            raise UnauthorizedException(message="Refresh token is invalid or expired.")
        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            raise UnauthorizedException(message="Invalid refresh token.") from exc
        if refresh_session.user_id != user_id:
            raise UnauthorizedException(message="Invalid refresh token.")
        user = await self.user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException(message="This account is inactive or no longer exists.")
        await self.refresh_session_repository.revoke(refresh_session, utcnow())
        return await self._create_token_pair(user)

    async def logout(self, refresh_token: str) -> None:
        """Revoke the supplied refresh token; logout remains safe and idempotent."""
        try:
            claims = self._decode_expected_token(refresh_token, REFRESH_TOKEN_TYPE)
        except UnauthorizedException:
            return
        token_identifier = claims.get("jti")
        if isinstance(token_identifier, str):
            refresh_session = await self.refresh_session_repository.get_active_by_token_hash(
                hash_token_identifier(token_identifier)
            )
            if refresh_session is not None:
                await self.refresh_session_repository.revoke(refresh_session, utcnow())

    async def get_current_user(self, token: str) -> User:
        """Return the active user represented by a valid access token."""
        claims = self._decode_expected_token(token, ACCESS_TOKEN_TYPE)
        subject = claims.get("sub")
        if not isinstance(subject, str):
            raise UnauthorizedException(message="Invalid access token.")
        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            raise UnauthorizedException(message="Invalid access token.") from exc
        user = await self.user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException(message="This account is inactive or no longer exists.")
        return user

    async def create_admin(
        self, *, email: str, username: str, full_name: str, password: str
    ) -> User | None:
        """Create the initial admin, or return None when an admin already exists."""
        if await self.user_repository.get_any_admin():
            return None
        if await self.user_repository.get_by_email(email):
            raise ConflictException(message="An account with this email already exists.")
        if await self.user_repository.get_by_username(username):
            raise ConflictException(message="This username is already in use.")
        return await self.user_repository.create(
            User(
                email=email, username=username, full_name=full_name, password_hash=hash_password(password),
                role=UserRole.ADMIN, is_active=True,
            )
        )

    async def _build_auth_response(self, user: User) -> AuthResponse:
        return AuthResponse(tokens=await self._create_token_pair(user), user=UserResponse.model_validate(user))

    async def _create_token_pair(self, user: User) -> TokenPairResponse:
        access_token = create_access_token(
            subject=str(user.id), role=user.role.value, settings=self.settings
        )
        refresh_token, token_identifier, expires_at = create_refresh_token(
            subject=str(user.id), settings=self.settings
        )
        await self.refresh_session_repository.create(
            RefreshSession(
                user_id=user.id, token_hash=hash_token_identifier(token_identifier), expires_at=expires_at
            )
        )
        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)

    def _decode_expected_token(self, token: str, expected_type: str) -> dict:
        try:
            claims = decode_token(token, self.settings)
        except JWTError as exc:
            raise UnauthorizedException(message="Token is invalid or expired.") from exc
        if claims.get("type") != expected_type:
            raise UnauthorizedException(message="Invalid token type.")
        return claims
