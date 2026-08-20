"""Pluggable object storage for uploaded images.

LocalStorage (filesystem) for dev/tests; S3Storage (S3 / Cloudflare R2) for prod.
Selected by config — the rest of the app just calls save/load/delete with an
opaque `location` string.
"""

import asyncio
import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles

from app.config import settings


class Storage(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes under `key`; return an opaque location for later load/delete."""

    @abstractmethod
    async def load(self, location: str) -> tuple[bytes, str] | None:
        """Return (data, content_type), or None if the object is missing."""

    @abstractmethod
    async def delete(self, location: str) -> None:
        """Remove the object (no error if already gone)."""


class LocalStorage(Storage):
    def __init__(self, base_dir: str | Path):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self.base / key
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return str(path)

    async def load(self, location: str) -> tuple[bytes, str] | None:
        path = Path(location)
        if not path.exists():
            return None
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return data, content_type

    async def delete(self, location: str) -> None:
        try:
            Path(location).unlink(missing_ok=True)
        except OSError:
            pass


class S3Storage(Storage):
    """S3-compatible storage (AWS S3 or Cloudflare R2). The `location` is the key."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str = "",
        region: str = "auto",
        access_key_id: str = "",
        secret_access_key: str = "",
    ):
        self.bucket = bucket
        self._endpoint_url = endpoint_url
        self._region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._client = None

    @property
    def client(self):
        # Created lazily so a storage misconfiguration can't crash app import.
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3",
                region_name=self._region or None,
                endpoint_url=self._endpoint_url or None,
                aws_access_key_id=self._access_key_id or None,
                aws_secret_access_key=self._secret_access_key or None,
            )
        return self._client

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def load(self, location: str) -> tuple[bytes, str] | None:
        def _get() -> tuple[bytes, str] | None:
            try:
                resp = self.client.get_object(Bucket=self.bucket, Key=location)
            except self.client.exceptions.NoSuchKey:
                return None
            return resp["Body"].read(), resp.get("ContentType", "application/octet-stream")

        return await asyncio.to_thread(_get)

    async def delete(self, location: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=location)


def get_storage() -> Storage:
    """Build the storage backend from configuration."""
    if settings.s3_bucket:
        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
        )
    return LocalStorage(settings.upload_dir)
