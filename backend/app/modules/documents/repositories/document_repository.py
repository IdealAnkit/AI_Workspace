"""Database-only operations for document metadata."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models.document import Document, DocumentStatus
from app.utils.datetime import utcnow


class DocumentRepository:
    """Encapsulates document metadata reads and writes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, document_id: UUID, *, include_deleted: bool = False) -> Document | None:
        """Retrieve metadata for internal modules without bypassing soft deletion."""
        conditions = [Document.id == document_id]
        if not include_deleted:
            conditions.append(Document.is_deleted.is_(False))
        result = await self.session.execute(select(Document).where(*conditions))
        return result.scalar_one_or_none()

    async def get_by_id_for_owner(
        self, document_id: UUID, owner_id: UUID, *, include_deleted: bool = False
    ) -> Document | None:
        conditions = [Document.id == document_id, Document.owner_id == owner_id]
        if not include_deleted:
            conditions.append(Document.is_deleted.is_(False))
        result = await self.session.execute(select(Document).where(*conditions))
        return result.scalar_one_or_none()

    async def get_by_checksum_for_owner(
        self, checksum_sha256: str, owner_id: UUID, *, include_deleted: bool = False
    ) -> Document | None:
        conditions = [
            Document.checksum_sha256 == checksum_sha256,
            Document.owner_id == owner_id,
        ]
        if not include_deleted:
            conditions.append(Document.is_deleted.is_(False))
        result = await self.session.execute(select(Document).where(*conditions))
        return result.scalar_one_or_none()

    async def list_for_owner(
        self, owner_id: UUID, offset: int, limit: int, *, include_deleted: bool = False
    ) -> tuple[list[Document], int]:
        conditions = [Document.owner_id == owner_id]
        if not include_deleted:
            conditions.append(Document.is_deleted.is_(False))
        documents_result = await self.session.execute(
            select(Document)
            .where(*conditions)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total_result = await self.session.execute(
            select(func.count()).select_from(Document).where(*conditions)
        )
        return list(documents_result.scalars().all()), int(total_result.scalar_one())

    async def create(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def delete(self, document: Document) -> None:
        """Retain deprecated hard-delete behavior for explicit maintenance tasks only."""
        await self.session.delete(document)
        await self.session.flush()

    async def soft_delete(self, document: Document, deleted_by: UUID) -> None:
        """Mark metadata deleted without removing its database record."""
        now = utcnow()
        document.is_deleted = True
        document.deleted_at = now
        document.deleted_by = deleted_by
        document.updated_by = deleted_by
        document.status = DocumentStatus.DELETED.value
        await self.session.flush()

    async def transition_status(
        self, document: Document, status: DocumentStatus, updated_by: UUID | None
    ) -> None:
        """Persist a lifecycle status and its actor when supplied."""
        document.status = status.value
        if updated_by is not None:
            document.updated_by = updated_by
        await self.session.flush()

    async def record_access(self, document: Document, accessed_by: UUID) -> None:
        """Maintain download analytics and audit fields."""
        document.last_accessed_at = utcnow()
        document.download_count += 1
        document.updated_by = accessed_by
        await self.session.flush()
