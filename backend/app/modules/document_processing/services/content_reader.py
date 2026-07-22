"""Provider-neutral source content reader used only by the processing service."""

from abc import ABC, abstractmethod

from app.modules.documents.models.document import Document
from app.modules.documents.storage.base import StorageProviderError
from app.modules.documents.storage.manager import StorageManager


class DocumentContentReader(ABC):
    """Read document bytes without exposing a concrete object-storage implementation."""

    @abstractmethod
    async def read(self, document: Document) -> bytes:
        """Return source bytes for one private document."""


class StorageManagerContentReader(DocumentContentReader):
    """Adapt the existing StorageManager contract to processing input bytes."""

    def __init__(self, storage_manager: StorageManager) -> None:
        self.storage_manager = storage_manager

    async def read(self, document: Document) -> bytes:
        try:
            download = await self.storage_manager.get_object(key=document.storage_key)
            try:
                return b"".join(download.chunks)
            finally:
                download.close()
        except StorageProviderError:
            raise
