"""Database-only persistence for processing jobs, logs, errors, and results."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models.document import Document
from app.modules.document_processing.models.processing import (
    ProcessedDocument,
    ProcessingError,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingLog,
)


class ProcessingRepository:
    """Encapsulates durable processing state with no parser or storage calls."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(self, document_id: UUID) -> ProcessingJob:
        job = ProcessingJob(document_id=document_id, status=ProcessingJobStatus.QUEUED.value)
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_job_for_owner(self, job_id: UUID, owner_id: UUID) -> ProcessingJob | None:
        result = await self.session.execute(
            select(ProcessingJob)
            .join(Document, ProcessingJob.document_id == Document.id)
            .where(
                ProcessingJob.id == job_id,
                Document.owner_id == owner_id,
                Document.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_jobs_for_owner(self, owner_id: UUID, offset: int, limit: int) -> tuple[list[ProcessingJob], int]:
        conditions = (Document.owner_id == owner_id, Document.is_deleted.is_(False))
        jobs_result = await self.session.execute(
            select(ProcessingJob)
            .join(Document, ProcessingJob.document_id == Document.id)
            .where(*conditions)
            .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total_result = await self.session.execute(
            select(func.count())
            .select_from(ProcessingJob)
            .join(Document, ProcessingJob.document_id == Document.id)
            .where(*conditions)
        )
        return list(jobs_result.scalars().all()), int(total_result.scalar_one())

    async def get_latest_job_for_document(self, document_id: UUID, owner_id: UUID) -> ProcessingJob | None:
        result = await self.session.execute(
            select(ProcessingJob)
            .join(Document, ProcessingJob.document_id == Document.id)
            .where(
                ProcessingJob.document_id == document_id,
                Document.owner_id == owner_id,
                Document.is_deleted.is_(False),
            )
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def set_job_processing(self, job: ProcessingJob, started_at: datetime) -> None:
        job.status = ProcessingJobStatus.PROCESSING.value
        job.started_at = started_at
        await self.session.flush()

    async def set_job_completed(self, job: ProcessingJob, finished_at: datetime, duration: float) -> None:
        job.status = ProcessingJobStatus.COMPLETED.value
        job.finished_at = finished_at
        job.duration_seconds = duration
        job.error_message = None
        await self.session.flush()

    async def set_job_failed(
        self, job: ProcessingJob, finished_at: datetime, duration: float, error_message: str
    ) -> None:
        job.status = ProcessingJobStatus.FAILED.value
        job.finished_at = finished_at
        job.duration_seconds = duration
        job.error_message = error_message
        await self.session.flush()

    async def add_log(self, job_id: UUID, level: str, message: str) -> ProcessingLog:
        log = ProcessingLog(processing_job_id=job_id, level=level, message=message)
        self.session.add(log)
        await self.session.flush()
        return log

    async def add_error(self, job_id: UUID, error_type: str, message: str) -> ProcessingError:
        error = ProcessingError(processing_job_id=job_id, error_type=error_type, message=message)
        self.session.add(error)
        await self.session.flush()
        return error

    async def list_logs_for_job(self, job_id: UUID) -> list[ProcessingLog]:
        result = await self.session.execute(
            select(ProcessingLog)
            .where(ProcessingLog.processing_job_id == job_id)
            .order_by(ProcessingLog.created_at.asc(), ProcessingLog.id.asc())
        )
        return list(result.scalars().all())

    async def get_result_for_document(self, document_id: UUID) -> ProcessedDocument | None:
        result = await self.session.execute(
            select(ProcessedDocument).where(ProcessedDocument.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_result_by_id(self, processed_document_id: UUID) -> ProcessedDocument | None:
        result = await self.session.execute(
            select(ProcessedDocument).where(ProcessedDocument.id == processed_document_id)
        )
        return result.scalar_one_or_none()

    async def upsert_result(self, parsed, job_id: UUID) -> ProcessedDocument:
        result = await self.get_result_for_document(parsed.document_id)
        values = {
            "processing_job_id": job_id,
            "title": parsed.title,
            "language": parsed.language,
            "page_count": parsed.page_count,
            "pages": [page.model_dump() for page in parsed.pages],
            "text": parsed.text,
            "metadata_": parsed.metadata,
            "warnings": parsed.warnings,
        }
        if result is None:
            result = ProcessedDocument(document_id=parsed.document_id, **values)
            self.session.add(result)
        else:
            for field, value in values.items():
                setattr(result, field, value)
        await self.session.flush()
        await self.session.refresh(result)
        return result
