"""Synchronous orchestration for the document processing foundation."""

import time
from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import InternalServerException, NotFoundException
from app.core.logging import get_logger
from app.modules.documents.models.document import (
    ALLOWED_DOCUMENT_STATUS_TRANSITIONS,
    Document,
    DocumentStatus,
)
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.storage.base import StorageProviderError
from app.modules.document_processing.events.base import (
    NoOpProcessingEventPublisher,
    ProcessingCompletedEvent,
    ProcessingEventPublisher,
)
from app.modules.document_processing.pipeline.pipeline import DocumentProcessingPipeline
from app.modules.document_processing.repositories.processing_repository import ProcessingRepository
from app.modules.document_processing.services.content_reader import DocumentContentReader
from app.utils.datetime import utcnow

logger = get_logger(__name__)


@dataclass
class ProcessingOverview:
    """Read-only view of the latest job and normalized result for one document."""

    job: object | None
    result: object | None


class ProcessingService:
    """Create jobs and orchestrate storage-independent processing stages."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        processing_repository: ProcessingRepository,
        content_reader: DocumentContentReader,
        pipeline: DocumentProcessingPipeline,
        event_publisher: ProcessingEventPublisher | None = None,
    ) -> None:
        self.document_repository = document_repository
        self.processing_repository = processing_repository
        self.content_reader = content_reader
        self.pipeline = pipeline
        self.event_publisher = event_publisher or NoOpProcessingEventPublisher()

    async def process_document(self, document_id: UUID) -> None:
        """Synchronously run one event-triggered processing attempt and persist all outcomes."""
        document = await self.document_repository.get_by_id(document_id)
        if document is None:
            logger.warning("Skipping processing for unavailable document %s", document_id)
            return

        job = await self.processing_repository.create_job(document.id)
        started_at = utcnow()
        started_clock = time.perf_counter()
        try:
            await self.processing_repository.add_log(job.id, "INFO", "Processing job queued.")
            await self._transition_document(document, DocumentStatus.QUEUED)
            await self.processing_repository.set_job_processing(job, started_at)
            await self._transition_document(document, DocumentStatus.PROCESSING)
            await self.processing_repository.add_log(job.id, "INFO", "Parser selection and extraction started.")
            content = await self.content_reader.read(document)
            parsed = await self.pipeline.process(document, content)
            result = await self.processing_repository.upsert_result(parsed, job.id)
            finished_at = utcnow()
            await self.processing_repository.set_job_completed(
                job, finished_at, time.perf_counter() - started_clock
            )
            await self._transition_document(document, DocumentStatus.READY)
            await self.processing_repository.add_log(job.id, "INFO", "Processing completed successfully.")
            processed_document_id = getattr(result, "id", None)
            if processed_document_id is None:
                logger.warning("Processed result has no persisted identifier; indexing event was skipped.")
            else:
                await self._publish_completed(processed_document_id, document.id, job.id, document.owner_id)
        except Exception as exc:
            finished_at = utcnow()
            duration = time.perf_counter() - started_clock
            message = str(exc) or exc.__class__.__name__
            logger.exception("Document processing failed for %s", document.id)
            await self.processing_repository.set_job_failed(job, finished_at, duration, message)
            await self.processing_repository.add_error(job.id, exc.__class__.__name__, message)
            await self.processing_repository.add_log(job.id, "ERROR", "Processing failed; error persisted.")
            if DocumentStatus.FAILED in ALLOWED_DOCUMENT_STATUS_TRANSITIONS[DocumentStatus(document.status)]:
                await self._transition_document(document, DocumentStatus.FAILED)

    async def get_job(self, job_id: UUID, owner_id: UUID):
        """Return one owner-scoped processing job."""
        job = await self.processing_repository.get_job_for_owner(job_id, owner_id)
        if job is None:
            raise NotFoundException(message="Processing job not found.")
        return job

    async def list_jobs(self, owner_id: UUID, offset: int, limit: int) -> tuple[list, int]:
        """List only jobs belonging to the authenticated user's documents."""
        return await self.processing_repository.list_jobs_for_owner(owner_id, offset, limit)

    async def get_logs(self, job_id: UUID, owner_id: UUID) -> list:
        """Return owner-scoped logs after authorizing access to their job."""
        await self.get_job(job_id, owner_id)
        return await self.processing_repository.list_logs_for_job(job_id)

    async def get_document_overview(self, document_id: UUID, owner_id: UUID) -> ProcessingOverview:
        """Return processing state for one owned document without triggering work."""
        document = await self.document_repository.get_by_id_for_owner(document_id, owner_id)
        if document is None:
            raise NotFoundException(message="Document not found.")
        job = await self.processing_repository.get_latest_job_for_document(document_id, owner_id)
        result = await self.processing_repository.get_result_for_document(document_id)
        return ProcessingOverview(job=job, result=result)

    async def _transition_document(self, document: Document, target: DocumentStatus) -> None:
        current = DocumentStatus(document.status)
        if target not in ALLOWED_DOCUMENT_STATUS_TRANSITIONS[current]:
            raise InternalServerException(
                message=f"Invalid processing lifecycle transition from {current.value} to {target.value}."
            )
        await self.document_repository.transition_status(document, target, updated_by=None)

    async def _publish_completed(self, processed_document_id: UUID, document_id: UUID, job_id: UUID, owner_id: UUID) -> None:
        try:
            await self.event_publisher.publish(
                ProcessingCompletedEvent(
                    processed_document_id=processed_document_id,
                    document_id=document_id,
                    processing_job_id=job_id,
                    owner_id=owner_id,
                    occurred_at=utcnow(),
                )
            )
        except Exception:
            logger.exception("Processing completion event publication failed for %s", processed_document_id)
