"""Public request-independent schemas for document processing state."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.document_processing.models.processing import ProcessingJobStatus


class ProcessingJobResponse(BaseModel):
    """Durable state of one processing attempt."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    status: ProcessingJobStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    error_message: str | None
    attempts: int
    created_at: datetime
    updated_at: datetime


class ProcessingLogResponse(BaseModel):
    """A timestamped, non-sensitive processing log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    processing_job_id: UUID
    level: str
    message: str
    created_at: datetime


class ProcessedDocumentResponse(BaseModel):
    """Normalized extraction result for an owned document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    processing_job_id: UUID | None
    title: str | None
    language: str | None
    page_count: int | None
    pages: list[dict[str, Any]]
    text: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    warnings: list[str]
    created_at: datetime
    updated_at: datetime


class DocumentProcessingResponse(BaseModel):
    """Latest job plus result, if extraction completed."""

    job: ProcessingJobResponse | None
    result: ProcessedDocumentResponse | None
