"""Pydantic schemas that expose document metadata without storage internals."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.documents.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Safe document metadata returned to its owner."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "b251a41d-73a1-451f-b8c3-55ceef4e7f08",
                "owner_id": "96d7ee8e-c6ab-47f0-acd3-77a7d81814f5",
                "workspace_id": None,
                "filename": "architecture-overview.pdf",
                "original_filename": "architecture-overview.pdf",
                "mime_type": "application/pdf",
                "extension": ".pdf",
                "size_bytes": 248921,
                "checksum_sha256": "8f1bb4c7a0ad94e6561bd22615f2c95b6ee3155dd1e23cdd7d18fd4f83075b37",
                "status": "stored",
                "upload_status": "stored",
                "page_count": None,
                "language": None,
                "metadata": {},
                "version": 1,
                "is_latest_version": True,
                "parent_document_id": None,
                "parent_folder_id": None,
                "download_count": 0,
                "last_accessed_at": None,
                "created_at": "2026-07-23T10:30:00Z",
                "updated_at": "2026-07-23T10:30:00Z",
            }
        },
    )

    id: UUID
    owner_id: UUID
    workspace_id: UUID | None
    filename: str
    original_filename: str
    mime_type: str
    extension: str
    size_bytes: int
    checksum_sha256: str
    status: DocumentStatus
    upload_status: DocumentStatus = Field(validation_alias="status", description="Deprecated alias for status.")
    page_count: int | None
    language: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    parent_document_id: UUID | None
    version: int | None
    is_latest_version: bool | None
    parent_folder_id: UUID | None
    uploaded_by: UUID
    updated_by: UUID | None
    deleted_by: UUID | None
    deleted_at: datetime | None
    is_deleted: bool
    last_accessed_at: datetime | None
    download_count: int
    created_at: datetime
    updated_at: datetime


class SignedDownloadResponse(BaseModel):
    """Temporary provider-generated URL for a private document download."""

    document_id: UUID
    download_url: str
    expires_in_seconds: int
