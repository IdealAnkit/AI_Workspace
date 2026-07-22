"""Provider-independent tests for document business workflows."""

import io
import unittest
import uuid
from datetime import UTC, datetime

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.user import User
from app.modules.documents.events.base import (
    DocumentDeletedEvent,
    DocumentEventPublisher,
    DocumentUploadedEvent,
)
from app.modules.documents.models.document import Document, DocumentStatus
from app.modules.documents.services.document_service import (
    DocumentService,
    SignedDocumentDownload,
)
from app.modules.documents.storage.base import StorageDownload


class InMemoryDocumentRepository:
    """Repository double used to test service behavior without a database."""

    def __init__(self, document: Document | None = None, duplicate: Document | None = None) -> None:
        self.document = document
        self.duplicate = duplicate
        self.created: Document | None = None
        self.accesses = 0

    async def get_by_checksum_for_owner(self, checksum_sha256: str, owner_id: uuid.UUID) -> Document | None:
        return self.duplicate

    async def create(self, document: Document) -> Document:
        self.created = document
        self.document = document
        return document

    async def get_by_id_for_owner(
        self, document_id: uuid.UUID, owner_id: uuid.UUID, *, include_deleted: bool = False
    ) -> Document | None:
        if self.document and self.document.id == document_id and self.document.owner_id == owner_id:
            if include_deleted or not self.document.is_deleted:
                return self.document
        return None

    async def soft_delete(self, document: Document, deleted_by: uuid.UUID) -> None:
        document.is_deleted = True
        document.deleted_by = deleted_by
        document.updated_by = deleted_by
        document.deleted_at = datetime.now(UTC)
        document.status = DocumentStatus.DELETED.value

    async def transition_status(
        self, document: Document, status: DocumentStatus, updated_by: uuid.UUID | None
    ) -> None:
        document.status = status.value
        document.updated_by = updated_by

    async def record_access(self, document: Document, accessed_by: uuid.UUID) -> None:
        self.accesses += 1
        document.download_count += 1
        document.updated_by = accessed_by


class InMemoryStorageManager:
    """Storage-manager double that captures bytes and can issue signed URLs."""

    provider_name = "memory"

    def __init__(self, signed_url: str | None = None) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted_keys: list[str] = []
        self.signed_url = signed_url

    async def put_object(
        self, *, key: str, data: io.BufferedIOBase, size_bytes: int, mime_type: str
    ) -> None:
        self.objects[key] = data.read()

    async def get_object(self, *, key: str) -> StorageDownload:
        return StorageDownload(chunks=[self.objects[key]], close=lambda: None)

    async def delete_object(self, *, key: str) -> None:
        self.deleted_keys.append(key)
        self.objects.pop(key, None)

    async def get_signed_download_url(self, *, key: str, expires_in_seconds: int) -> str | None:
        return self.signed_url


class RecordingEventPublisher(DocumentEventPublisher):
    """Event double that records local lifecycle events."""

    def __init__(self) -> None:
        self.events: list[DocumentUploadedEvent | DocumentDeletedEvent] = []

    async def publish(self, event: DocumentUploadedEvent | DocumentDeletedEvent) -> None:
        self.events.append(event)


class DocumentServiceTests(unittest.IsolatedAsyncioTestCase):
    """Validate storage-independent document-service behavior."""

    def setUp(self) -> None:
        self.owner = User(id=uuid.uuid4())

    def build_service(
        self,
        repository: InMemoryDocumentRepository,
        storage: InMemoryStorageManager,
        events: RecordingEventPublisher | None = None,
        *,
        delete_storage_objects: bool = False,
    ) -> DocumentService:
        return DocumentService(
            repository=repository,
            storage_manager=storage,  # type: ignore[arg-type]
            event_publisher=events or RecordingEventPublisher(),
            max_file_size_bytes=1024,
            signed_url_expiration_seconds=900,
            delete_storage_objects=delete_storage_objects,
        )

    async def test_upload_persists_metadata_private_key_and_event(self) -> None:
        repository = InMemoryDocumentRepository()
        storage = InMemoryStorageManager()
        events = RecordingEventPublisher()
        service = self.build_service(repository, storage, events)
        upload = UploadFile(
            io.BytesIO(b"hello document"),
            filename="notes.md",
            headers=Headers({"content-type": "text/markdown"}),
        )

        document = await service.upload(upload, self.owner)

        self.assertEqual(document.status, DocumentStatus.STORED.value)
        self.assertEqual(document.version, 1)
        self.assertTrue(document.is_latest_version)
        self.assertEqual(document.uploaded_by, self.owner.id)
        self.assertTrue(document.storage_key.startswith(f"documents/{self.owner.id}/"))
        self.assertNotIn(document.filename, document.storage_key)
        self.assertEqual(storage.objects[document.storage_key], b"hello document")
        self.assertIsInstance(events.events[0], DocumentUploadedEvent)

    async def test_duplicate_checksum_is_rejected_before_storage_write(self) -> None:
        repository = InMemoryDocumentRepository(duplicate=Document(id=uuid.uuid4()))
        storage = InMemoryStorageManager()
        service = self.build_service(repository, storage)
        upload = UploadFile(
            io.BytesIO(b"duplicate"),
            filename="duplicate.txt",
            headers=Headers({"content-type": "text/plain"}),
        )

        with self.assertRaises(ConflictException):
            await service.upload(upload, self.owner)
        self.assertEqual(storage.objects, {})

    async def test_empty_file_is_rejected(self) -> None:
        service = self.build_service(InMemoryDocumentRepository(), InMemoryStorageManager())
        upload = UploadFile(
            io.BytesIO(),
            filename="empty.txt",
            headers=Headers({"content-type": "text/plain"}),
        )

        with self.assertRaises(ValidationException):
            await service.upload(upload, self.owner)

    async def test_soft_delete_hides_document_and_emits_event(self) -> None:
        document = self.make_document()
        repository = InMemoryDocumentRepository(document=document)
        storage = InMemoryStorageManager()
        events = RecordingEventPublisher()
        service = self.build_service(repository, storage, events)

        await service.delete(document.id, self.owner.id)

        self.assertTrue(document.is_deleted)
        self.assertEqual(document.status, DocumentStatus.DELETED.value)
        self.assertEqual(storage.deleted_keys, [])
        self.assertIsInstance(events.events[0], DocumentDeletedEvent)
        with self.assertRaises(NotFoundException):
            await service.get(document.id, self.owner.id)

    async def test_status_transition_and_signed_download_are_recorded(self) -> None:
        document = self.make_document()
        repository = InMemoryDocumentRepository(document=document)
        storage = InMemoryStorageManager(signed_url="https://storage.example/signed")
        service = self.build_service(repository, storage)

        transitioned = await service.transition_status(
            document.id, self.owner.id, DocumentStatus.QUEUED, self.owner.id
        )
        result = await service.download(document.id, self.owner.id, "signed")

        self.assertEqual(transitioned.status, DocumentStatus.QUEUED.value)
        self.assertIsInstance(result, SignedDocumentDownload)
        self.assertEqual(result.url, "https://storage.example/signed")
        self.assertEqual(repository.accesses, 1)

    def make_document(self) -> Document:
        return Document(
            id=uuid.uuid4(),
            owner_id=self.owner.id,
            filename="notes.txt",
            original_filename="notes.txt",
            mime_type="text/plain",
            extension=".txt",
            size_bytes=5,
            checksum_sha256="a" * 64,
            storage_key=f"documents/{self.owner.id}/aa/{'a' * 64}.txt",
            storage_provider="memory",
            status=DocumentStatus.STORED.value,
            uploaded_by=self.owner.id,
            updated_by=self.owner.id,
            version=1,
            is_latest_version=True,
            is_deleted=False,
            download_count=0,
            metadata_={},
        )
