"""Storage abstraction used by document services, independent of MinIO."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import BinaryIO


class StorageProviderError(Exception):
    """Raised when an underlying object-storage operation cannot complete."""


@dataclass
class StorageDownload:
    """A provider-neutral byte stream plus its resource cleanup callback."""

    chunks: Iterable[bytes]
    close: Callable[[], None]


class StorageProvider(ABC):
    """Contract for durable document-byte storage providers."""

    name: str
    supports_signed_urls: bool = False

    @abstractmethod
    async def put_object(
        self,
        *,
        key: str,
        data: BinaryIO,
        size_bytes: int,
        mime_type: str,
    ) -> None:
        """Store bytes under a private provider key."""

    @abstractmethod
    async def get_object(self, *, key: str) -> StorageDownload:
        """Open a private object for streamed download."""

    @abstractmethod
    async def delete_object(self, *, key: str) -> None:
        """Permanently remove a private object."""

    async def get_signed_download_url(self, *, key: str, expires_in_seconds: int) -> str | None:
        """Return a temporary URL when the provider supports direct downloads."""
        return None
