"""Database access for users and refresh sessions only."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshSession, User, UserRole


class UserRepository:
    """Encapsulates all user persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_any_admin(self) -> User | None:
        result = await self.session.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user


class RefreshSessionRepository:
    """Encapsulates refresh-session persistence and revocation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, refresh_session: RefreshSession) -> RefreshSession:
        self.session.add(refresh_session)
        await self.session.flush()
        return refresh_session

    async def get_active_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        result = await self.session.execute(
            select(RefreshSession).where(
                RefreshSession.token_hash == token_hash,
                RefreshSession.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, refresh_session: RefreshSession, revoked_at: datetime) -> None:
        refresh_session.revoked_at = revoked_at
        await self.session.flush()
