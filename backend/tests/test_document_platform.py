"""Tests for repository filtering, API protection, and storage-manager capabilities."""

import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundException
from app.core.app_factory import create_app
from app.modules.documents.dependencies import get_document_service
from app.modules.documents.models.document import Document, DocumentStatus
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.services.document_service import SignedDocumentDownload
from app.modules.documents.storage.manager import StorageManager
from app.modules.documents.storage.minio import MinIOStorageProvider
from app.config.settings import Settings
from app.models.user import User


class ScalarResult:
    """Tiny result double compatible with repository scalar access."""

    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value

    def scalar_one(self) -> object:
        return self.value


class DocumentRowsResult:
    """Result double for list query scalar rows."""

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def scalars(self) -> "DocumentRowsResult":
        return self

    def all(self) -> list[Document]:
        return self.documents


class CapturingSession:
    """Async-session double that records statements without a database."""

    def __init__(self, results: list[object]) -> None:
        self.results = iter(results)
        self.statements: list[object] = []
        self.flush_count = 0

    async def execute(self, statement: object) -> object:
        self.statements.append(statement)
        return next(self.results)

    async def flush(self) -> None:
        self.flush_count += 1


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    """Ensure document metadata queries exclude soft-deleted rows by default."""

    async def test_get_and_list_queries_filter_soft_deleted_documents(self) -> None:
        session = CapturingSession([ScalarResult(None), DocumentRowsResult([]), ScalarResult(0)])
        repository = DocumentRepository(session)  # type: ignore[arg-type]
        owner_id = uuid.uuid4()

        await repository.get_by_id_for_owner(uuid.uuid4(), owner_id)
        await repository.list_for_owner(owner_id, offset=0, limit=20)

        compiled = "\n".join(str(statement) for statement in session.statements)
        self.assertIn("documents.is_deleted IS false", compiled)

    async def test_soft_delete_marks_lifecycle_and_audit_fields(self) -> None:
        session = CapturingSession([])
        repository = DocumentRepository(session)  # type: ignore[arg-type]
        actor = uuid.uuid4()
        document = make_document(owner_id=actor)

        await repository.soft_delete(document, actor)

        self.assertTrue(document.is_deleted)
        self.assertEqual(document.status, DocumentStatus.DELETED.value)
        self.assertEqual(document.deleted_by, actor)
        self.assertEqual(session.flush_count, 1)


class StorageManagerTests(unittest.IsolatedAsyncioTestCase):
    """Test configuration resolution and signed URL capability without MinIO I/O."""

    async def test_minio_manager_resolution_and_signed_url_generation(self) -> None:
        settings = Settings(DOCUMENT_STORAGE_PROVIDER="minio", MINIO_BUCKET="documents")
        manager = StorageManager.from_settings(settings)
        self.assertEqual(manager.provider_name, "minio")
        self.assertTrue(manager.supports_signed_urls)

        provider = MinIOStorageProvider(settings)
        provider.client = MagicMock()
        provider.client.presigned_get_object.return_value = "https://storage.example/signed"
        url = await provider.get_signed_download_url(key="documents/key", expires_in_seconds=900)

        self.assertEqual(url, "https://storage.example/signed")
        provider.client.presigned_get_object.assert_called_once()

    async def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            StorageManager({}, "unknown")


class ApiDocumentService:
    """Endpoint-service double used without a database or object-storage server."""

    def __init__(self, document: Document) -> None:
        self.document = document
        self.deleted: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def upload(self, file: object, user: User) -> Document:
        return self.document

    async def get(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> Document:
        if document_id != self.document.id:
            raise NotFoundException(message="Document not found.")
        return self.document

    async def list(self, owner_id: uuid.UUID, page: int, size: int):
        return type("Page", (), {"documents": [self.document], "total": 1})()

    async def delete(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        self.deleted.append((document_id, owner_id))

    async def download(self, document_id: uuid.UUID, owner_id: uuid.UUID, delivery: str):
        if delivery == "signed":
            return SignedDocumentDownload(self.document, "https://storage.example/signed", 900)
        raise NotFoundException(message="Streaming test not configured.")


class ApiTests(unittest.TestCase):
    """Document endpoints stay bearer-protected and preserve response envelopes."""

    def setUp(self) -> None:
        self.app = create_app()
        self.owner = User(id=uuid.uuid4())
        self.document = make_document(owner_id=self.owner.id)
        self.service = ApiDocumentService(self.document)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_documents_require_authentication(self) -> None:
        with TestClient(self.app) as client:
            response = client.get("/api/v1/documents")
        self.assertEqual(response.status_code, 403)

    def test_upload_and_signed_download_use_existing_response_envelope(self) -> None:
        self.app.dependency_overrides[get_current_user] = lambda: self.owner
        self.app.dependency_overrides[get_document_service] = lambda: self.service

        with TestClient(self.app) as client:
            upload_response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("architecture.pdf", b"%PDF", "application/pdf")},
            )
            signed_response = client.get(
                f"/api/v1/documents/{self.document.id}/download?delivery=signed"
            )

        self.assertEqual(upload_response.status_code, 201)
        self.assertTrue(upload_response.json()["success"])
        self.assertEqual(upload_response.json()["data"]["status"], "stored")
        self.assertEqual(signed_response.status_code, 200)
        self.assertEqual(signed_response.json()["data"]["expires_in_seconds"], 900)


def make_document(owner_id: uuid.UUID) -> Document:
    """Build complete metadata suitable for response serialization tests."""
    return Document(
        id=uuid.uuid4(),
        owner_id=owner_id,
        filename="architecture.pdf",
        original_filename="architecture.pdf",
        mime_type="application/pdf",
        extension=".pdf",
        size_bytes=248921,
        checksum_sha256="a" * 64,
        storage_key=f"documents/{owner_id}/aa/{'a' * 64}.pdf",
        storage_provider="memory",
        status=DocumentStatus.STORED.value,
        uploaded_by=owner_id,
        updated_by=owner_id,
        version=1,
        is_latest_version=True,
        is_deleted=False,
        download_count=0,
        metadata_={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
