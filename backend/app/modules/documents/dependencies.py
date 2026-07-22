"""FastAPI dependencies specific to the documents feature module."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.api.deps import DatabaseDep, SettingsDep
from app.config.settings import get_settings
from app.modules.documents.events.base import DocumentEventPublisher, NoOpDocumentEventPublisher
from app.modules.document_processing.dependencies import get_document_event_publisher
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.services.document_service import DocumentService
from app.modules.documents.storage.manager import StorageManager


@lru_cache
def get_document_storage_manager() -> StorageManager:
    """Return the process-wide configured document storage manager."""
    return StorageManager.from_settings(get_settings())


def get_document_service(
    db: DatabaseDep,
    settings: SettingsDep,
    storage_manager: Annotated[StorageManager, Depends(get_document_storage_manager)],
    event_publisher: Annotated[DocumentEventPublisher, Depends(get_document_event_publisher)],
) -> DocumentService:
    """Build a request-scoped document service around shared infrastructure."""
    return DocumentService(
        repository=DocumentRepository(db),
        storage_manager=storage_manager,
        event_publisher=event_publisher if settings.DOCUMENT_PROCESSING_ENABLED else NoOpDocumentEventPublisher(),
        max_file_size_bytes=settings.DOCUMENT_MAX_FILE_SIZE_BYTES,
        signed_url_expiration_seconds=settings.SIGNED_URL_EXPIRATION,
        delete_storage_objects=settings.DOCUMENT_DELETE_STORAGE_OBJECTS,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
