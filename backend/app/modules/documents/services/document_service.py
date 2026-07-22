"""Document business workflows, independent from any specific storage implementation."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictException, InternalServerException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.models.user import User
from app.modules.documents.events.base import (
    DocumentDeletedEvent,
    DocumentEventPublisher,
    DocumentUploadedEvent,
)
from app.modules.documents.models.document import Document, DocumentStatus
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.storage.base import StorageDownload, StorageProviderError
from app.modules.documents.storage.manager import StorageManager
from app.utils.datetime import utcnow
from app.utils.pagination import get_offset

SUPPORTED_DOCUMENT_TYPES: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "text/plain": {".txt", ".md", ".markdown"},
    "text/markdown": {".md", ".markdown"},
    "text/x-markdown": {".md", ".markdown"},
}
UPLOAD_READ_CHUNK_SIZE = 1024 * 1024
ALLOWED_STATUS_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.UPLOADING: {DocumentStatus.STORED, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.STORED: {DocumentStatus.QUEUED, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.QUEUED: {DocumentStatus.PROCESSING, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.PROCESSING: {DocumentStatus.READY, DocumentStatus.FAILED, DocumentStatus.DELETED},
    DocumentStatus.READY: {DocumentStatus.QUEUED, DocumentStatus.DELETED},
    DocumentStatus.FAILED: {DocumentStatus.QUEUED, DocumentStatus.DELETED},
    DocumentStatus.DELETED: set(),
}
logger = get_logger(__name__)


@dataclass
class DocumentPage:
    """A page of owner-scoped document metadata."""

    documents: list[Document]
    total: int


@dataclass
class DocumentDownload:
    """Metadata and provider-neutral stream required by the download endpoint."""

    document: Document
    storage_download: StorageDownload


@dataclass
class SignedDocumentDownload:
    """Provider-generated private download URL and its configured expiry."""

    document: Document
    url: str
    expires_in_seconds: int


class DocumentService:
    """Coordinates validation, storage, and metadata persistence for documents."""

    def __init__(
        self,
        repository: DocumentRepository,
        storage_manager: StorageManager,
        event_publisher: DocumentEventPublisher,
        max_file_size_bytes: int,
        signed_url_expiration_seconds: int,
        delete_storage_objects: bool,
    ) -> None:
        self.repository = repository
        self.storage_manager = storage_manager
        self.event_publisher = event_publisher
        self.max_file_size_bytes = max_file_size_bytes
        self.signed_url_expiration_seconds = signed_url_expiration_seconds
        self.delete_storage_objects = delete_storage_objects

    async def upload(self, upload: UploadFile, owner: User) -> Document:
        """Validate, store, and persist metadata for a user-owned document."""
        filename, extension, mime_type = self._validate_upload_metadata(upload)
        buffered_file, size_bytes, checksum_sha256 = await self._buffer_upload(upload)
        storage_key = self._build_storage_key(owner.id, checksum_sha256, extension)

        try:
            if await self.repository.get_by_checksum_for_owner(checksum_sha256, owner.id):
                raise ConflictException(message="This document has already been uploaded.")

            try:
                await self.storage_manager.put_object(
                    key=storage_key,
                    data=buffered_file,
                    size_bytes=size_bytes,
                    mime_type=mime_type,
                )
            except StorageProviderError as exc:
                raise InternalServerException(message="Document storage is currently unavailable.") from exc

            document = Document(
                owner_id=owner.id,
                filename=filename,
                original_filename=filename,
                mime_type=mime_type,
                extension=extension,
                size_bytes=size_bytes,
                checksum_sha256=checksum_sha256,
                storage_key=storage_key,
                storage_provider=self.storage_manager.provider_name,
                status=DocumentStatus.STORED.value,
                uploaded_by=owner.id,
                updated_by=owner.id,
                version=1,
                is_latest_version=True,
            )
            try:
                created_document = await self.repository.create(document)
            except IntegrityError as exc:
                # A concurrent upload of the same bytes wins; the deterministic
                # provider key still points to identical content.
                raise ConflictException(message="This document has already been uploaded.") from exc
            await self._publish_event(
                DocumentUploadedEvent(
                    document_id=created_document.id,
                    owner_id=created_document.owner_id,
                    occurred_at=utcnow(),
                )
            )
            return created_document
        finally:
            buffered_file.close()
            await upload.close()

    async def get(self, document_id: UUID, owner_id: UUID) -> Document:
        """Get a document only when it is owned by the requesting user."""
        document = await self.repository.get_by_id_for_owner(document_id, owner_id)
        if document is None:
            raise NotFoundException(message="Document not found.")
        return document

    async def list(self, owner_id: UUID, page: int, size: int) -> DocumentPage:
        """List only the requesting user's documents."""
        documents, total = await self.repository.list_for_owner(owner_id, get_offset(page, size), size)
        return DocumentPage(documents=documents, total=total)

    async def delete(self, document_id: UUID, owner_id: UUID) -> None:
        """Soft-delete metadata and optionally remove storage-provider bytes."""
        document = await self.get(document_id, owner_id)
        if self.delete_storage_objects:
            try:
                await self.storage_manager.delete_object(key=document.storage_key)
            except StorageProviderError as exc:
                raise InternalServerException(message="Document storage is currently unavailable.") from exc
        await self.repository.soft_delete(document, owner_id)
        await self._publish_event(
            DocumentDeletedEvent(
                document_id=document.id,
                owner_id=document.owner_id,
                deleted_by=owner_id,
                occurred_at=document.deleted_at or utcnow(),
            )
        )

    async def download(
        self, document_id: UUID, owner_id: UUID, delivery: str = "stream"
    ) -> DocumentDownload | SignedDocumentDownload:
        """Open a streamed download or provider-signed URL for an owned document."""
        document = await self.get(document_id, owner_id)
        await self.repository.record_access(document, owner_id)
        if delivery in {"signed", "auto"}:
            try:
                signed_url = await self.storage_manager.get_signed_download_url(
                    key=document.storage_key,
                    expires_in_seconds=self.signed_url_expiration_seconds,
                )
            except StorageProviderError as exc:
                raise InternalServerException(message="Document storage is currently unavailable.") from exc
            if signed_url:
                return SignedDocumentDownload(
                    document=document,
                    url=signed_url,
                    expires_in_seconds=self.signed_url_expiration_seconds,
                )
            if delivery == "signed":
                raise ValidationException(message="Signed downloads are not supported by the active storage provider.")
        try:
            storage_download = await self.storage_manager.get_object(key=document.storage_key)
        except StorageProviderError as exc:
            raise InternalServerException(message="Document storage is currently unavailable.") from exc
        return DocumentDownload(document=document, storage_download=storage_download)

    async def transition_status(
        self,
        document_id: UUID,
        owner_id: UUID,
        target_status: DocumentStatus,
        updated_by: UUID | None = None,
    ) -> Document:
        """Validate and persist a future ingestion lifecycle transition."""
        document = await self.get(document_id, owner_id)
        current_status = DocumentStatus(document.status)
        if target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
            raise ValidationException(
                message=f"Invalid document status transition: {current_status.value} to {target_status.value}."
            )
        await self.repository.transition_status(document, target_status, updated_by)
        return document

    async def _publish_event(self, event: DocumentUploadedEvent | DocumentDeletedEvent) -> None:
        """Invoke the event contract without allowing future transport failures to break storage."""
        try:
            await self.event_publisher.publish(event)
        except Exception:
            logger.exception("Document event publication failed for %s", event)

    def _validate_upload_metadata(self, upload: UploadFile) -> tuple[str, str, str]:
        original_filename = upload.filename or ""
        filename = original_filename.strip()
        if not filename or len(filename) > 255:
            raise ValidationException(message="A filename between 1 and 255 characters is required.")
        if "\x00" in filename or "/" in filename or "\\" in filename:
            raise ValidationException(message="Filename must not contain path separators or null bytes.")

        extension = Path(filename).suffix.lower()
        mime_type = (upload.content_type or "").lower().strip()
        allowed_extensions = SUPPORTED_DOCUMENT_TYPES.get(mime_type)
        if allowed_extensions is None or extension not in allowed_extensions:
            raise ValidationException(
                message="Unsupported document type. Supported formats are PDF, DOCX, TXT, and Markdown."
            )
        return filename, extension, mime_type

    async def _buffer_upload(self, upload: UploadFile) -> tuple[BinaryIO, int, str]:
        buffered_file = SpooledTemporaryFile(max_size=UPLOAD_READ_CHUNK_SIZE, mode="w+b")
        checksum = hashlib.sha256()
        size_bytes = 0
        try:
            while chunk := await upload.read(UPLOAD_READ_CHUNK_SIZE):
                size_bytes += len(chunk)
                if size_bytes > self.max_file_size_bytes:
                    raise ValidationException(
                        message=f"Document exceeds the {self.max_file_size_bytes} byte upload limit."
                    )
                checksum.update(chunk)
                buffered_file.write(chunk)

            if size_bytes == 0:
                raise ValidationException(message="Empty files cannot be uploaded.")
            buffered_file.seek(0)
            return buffered_file, size_bytes, checksum.hexdigest()
        except Exception:
            buffered_file.close()
            await upload.close()
            raise

    @staticmethod
    def _build_storage_key(owner_id: UUID, checksum_sha256: str, extension: str) -> str:
        """Build a deterministic private key without using the user filename."""
        return f"documents/{owner_id}/{checksum_sha256[:2]}/{checksum_sha256}{extension}"
