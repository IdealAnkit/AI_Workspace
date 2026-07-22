"""MinIO-backed implementation of the document storage contract."""

import asyncio
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.config.settings import Settings
from app.modules.documents.storage.base import StorageDownload, StorageProvider, StorageProviderError


class MinIOStorageProvider(StorageProvider):
    """Store document bytes in the configured MinIO bucket."""

    name = "minio"
    supports_signed_urls = True

    def __init__(self, settings: Settings) -> None:
        self.bucket_name = settings.minio_bucket
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    async def put_object(
        self,
        *,
        key: str,
        data: BinaryIO,
        size_bytes: int,
        mime_type: str,
    ) -> None:
        try:
            await asyncio.to_thread(self._put_object, key, data, size_bytes, mime_type)
        except Exception as exc:
            raise StorageProviderError("Unable to store document bytes.") from exc

    async def get_object(self, *, key: str) -> StorageDownload:
        try:
            response = await asyncio.to_thread(self._get_object, key)
        except Exception as exc:
            raise StorageProviderError("Unable to retrieve document bytes.") from exc

        def close_response() -> None:
            response.close()
            response.release_conn()

        return StorageDownload(chunks=response.stream(32 * 1024), close=close_response)

    async def delete_object(self, *, key: str) -> None:
        try:
            await asyncio.to_thread(self._delete_object, key)
        except Exception as exc:
            raise StorageProviderError("Unable to delete document bytes.") from exc

    async def get_signed_download_url(self, *, key: str, expires_in_seconds: int) -> str | None:
        try:
            return await asyncio.to_thread(self._get_signed_download_url, key, expires_in_seconds)
        except Exception as exc:
            raise StorageProviderError("Unable to create a document download URL.") from exc

    def _ensure_bucket(self) -> None:
        if self.client.bucket_exists(self.bucket_name):
            return
        try:
            self.client.make_bucket(self.bucket_name)
        except S3Error as exc:
            if exc.code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                raise

    def _put_object(self, key: str, data: BinaryIO, size_bytes: int, mime_type: str) -> None:
        self._ensure_bucket()
        self.client.put_object(
            self.bucket_name,
            key,
            data,
            length=size_bytes,
            content_type=mime_type,
        )

    def _get_object(self, key: str):
        return self.client.get_object(self.bucket_name, key)

    def _delete_object(self, key: str) -> None:
        self.client.remove_object(self.bucket_name, key)

    def _get_signed_download_url(self, key: str, expires_in_seconds: int) -> str:
        return self.client.presigned_get_object(
            self.bucket_name,
            key,
            expires=timedelta(seconds=expires_in_seconds),
        )
