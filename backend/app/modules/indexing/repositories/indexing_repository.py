"""Database-only persistence for immutable chunks and indexing attempts."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.indexing.models import DocumentChunk, EmbeddingError, EmbeddingJob, EmbeddingJobStatus, EmbeddingLog, IndexMetadata
from app.modules.documents.models.document import Document


class IndexingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_index_metadata(self, *, document_id: UUID, processing_job_id: UUID | None, collection: str, provider: str, model: str, version: int, dimensions: int) -> IndexMetadata:
        item = IndexMetadata(document_id=document_id, processing_job_id=processing_job_id, vector_collection=collection, provider=provider, embedding_model=model, embedding_version=version, embedding_dimension=dimensions)
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def create_job(self, *, document_id: UUID, processing_job_id: UUID | None, index_metadata_id: UUID, provider: str, model: str, dimensions: int) -> EmbeddingJob:
        job = EmbeddingJob(document_id=document_id, processing_job_id=processing_job_id, index_metadata_id=index_metadata_id, provider=provider, embedding_model=model, embedding_dimension=dimensions, status=EmbeddingJobStatus.PENDING.value)
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def set_status(self, job: EmbeddingJob, metadata: IndexMetadata, status: EmbeddingJobStatus, *, started_at: datetime | None = None, finished_at: datetime | None = None, duration: float | None = None, reason: str | None = None) -> None:
        job.status = status.value
        metadata.status = status.value
        if started_at is not None:
            job.started_at = started_at
        if finished_at is not None:
            job.finished_at = finished_at
        if duration is not None:
            job.duration_seconds = duration
        job.failure_reason = reason
        if status is EmbeddingJobStatus.READY:
            metadata.indexed_at = finished_at
        await self.session.flush()

    async def create_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Persist chunks once; indexing code never updates an existing chunk version."""
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def add_log(self, job_id: UUID, level: str, message: str) -> None:
        self.session.add(EmbeddingLog(embedding_job_id=job_id, level=level, message=message))
        await self.session.flush()

    async def add_error(self, job_id: UUID, error_type: str, message: str) -> None:
        self.session.add(EmbeddingError(embedding_job_id=job_id, error_type=error_type, message=message))
        await self.session.flush()

    async def get_latest_metadata_for_document(self, document_id: UUID) -> IndexMetadata | None:
        result = await self.session.execute(select(IndexMetadata).where(IndexMetadata.document_id == document_id).order_by(IndexMetadata.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def get_latest_metadata_for_owner(self, document_id: UUID, owner_id: UUID) -> IndexMetadata | None:
        result = await self.session.execute(
            select(IndexMetadata)
            .join(Document, IndexMetadata.document_id == Document.id)
            .where(
                IndexMetadata.document_id == document_id,
                Document.owner_id == owner_id,
                Document.is_deleted.is_(False),
            )
            .order_by(IndexMetadata.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def semantic_search(self, *args, **kwargs) -> list:
        return []

    async def hybrid_search(self, *args, **kwargs) -> list:
        return []

    async def keyword_search(self, *args, **kwargs) -> list:
        return []
