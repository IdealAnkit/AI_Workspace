"""Provider-agnostic document storage manager resolved from application configuration."""

from typing import BinaryIO

from app.config.settings import Settings
from app.modules.documents.storage.base import StorageDownload, StorageProvider
from app.modules.documents.storage.minio import MinIOStorageProvider


class StorageManager:
    """Resolve one configured provider while presenting a stable storage contract."""

    def __init__(self, providers: dict[str, StorageProvider], active_provider: str) -> None:
        self._providers = providers
        self._active_provider = active_provider.lower()
        if self._active_provider not in providers:
            available = ", ".join(sorted(providers))
            raise ValueError(f"Unsupported document storage provider. Available providers: {available}.")

    @classmethod
    def from_settings(cls, settings: Settings) -> "StorageManager":
        """Construct the configured manager and register built-in providers."""
        providers: dict[str, StorageProvider] = {"minio": MinIOStorageProvider(settings)}
        return cls(providers, settings.DOCUMENT_STORAGE_PROVIDER)

    @property
    def provider_name(self) -> str:
        return self._active_provider

    @property
    def supports_signed_urls(self) -> bool:
        return self._provider.supports_signed_urls

    async def put_object(
        self, *, key: str, data: BinaryIO, size_bytes: int, mime_type: str
    ) -> None:
        await self._provider.put_object(
            key=key, data=data, size_bytes=size_bytes, mime_type=mime_type
        )

    async def get_object(self, *, key: str) -> StorageDownload:
        return await self._provider.get_object(key=key)

    async def delete_object(self, *, key: str) -> None:
        await self._provider.delete_object(key=key)

    async def get_signed_download_url(self, *, key: str, expires_in_seconds: int) -> str | None:
        return await self._provider.get_signed_download_url(
            key=key, expires_in_seconds=expires_in_seconds
        )

    @property
    def _provider(self) -> StorageProvider:
        return self._providers[self._active_provider]
