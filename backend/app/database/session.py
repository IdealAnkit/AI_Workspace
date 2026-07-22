"""
Database session dependency.

Provides the get_db() async generator used as a FastAPI dependency.
Handles commit on success and rollback on any exception automatically.

Usage (via app/api/deps.py):
    from app.api.deps import DatabaseDep

    @router.get("/items")
    async def list_items(db: DatabaseDep):
        result = await db.execute(select(Item))
        ...
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency.

    Yields a session, commits on success, rolls back on any exception,
    and always closes the session when the request is done.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
