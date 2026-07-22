"""Document metadata model. File bytes remain in the configured storage provider."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.utils.datetime import utcnow


class DocumentStatus(str, Enum):
    """Lifecycle states used by storage and future ingestion workflows."""

    UPLOADING = "uploading"
    STORED = "stored"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


ALLOWED_DOCUMENT_STATUS_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.UPLOADING: {DocumentStatus.STORED, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.STORED: {DocumentStatus.QUEUED, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.QUEUED: {DocumentStatus.PROCESSING, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.PROCESSING: {DocumentStatus.READY, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.READY: {DocumentStatus.QUEUED, DocumentStatus.DELETED},
    DocumentStatus.FAILED: {DocumentStatus.QUEUED, DocumentStatus.DELETED},
    DocumentStatus.DELETED: set(),
}


class Document(Base):
    """Metadata for a file owned by one authenticated user."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        UniqueConstraint("owner_id", "checksum_sha256", name="owner_checksum_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentStatus.STORED.value, index=True
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    is_latest_version: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
