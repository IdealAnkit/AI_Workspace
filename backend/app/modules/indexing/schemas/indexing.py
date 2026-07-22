"""Safe, owner-visible index metadata schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.indexing.models import EmbeddingJobStatus


class IndexMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    processing_job_id: UUID | None
    vector_collection: str
    provider: str
    embedding_model: str
    embedding_version: int
    embedding_dimension: int
    chunk_count: int
    status: EmbeddingJobStatus
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime
