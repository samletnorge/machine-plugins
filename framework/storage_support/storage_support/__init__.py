"""Storage support plugin — registers storage backend implementations.

Uses existing 'storage-backend' category from memory_support.
Provides LocalStorageBackend and a boto3-backed S3StorageBackend.
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# --- Models ---


@dataclass
class StorageObject:
    key: str
    data: bytes
    content_type: str = "application/octet-stream"
    metadata: dict[str, Any] = field(default_factory=dict)
    size: int = 0

    def __post_init__(self):
        if self.size == 0:
            self.size = len(self.data)


# --- Base class ---


class StorageBackend(ABC):
    @abstractmethod
    async def get(self, bucket: str, key: str) -> StorageObject: ...

    @abstractmethod
    async def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> StorageObject: ...

    @abstractmethod
    async def delete(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    async def list(self, bucket: str, prefix: str = "") -> list[str]: ...


# --- Local Storage Backend ---


class LocalStorageBackend(StorageBackend):
    """File-system based storage backend."""

    def __init__(self, base_path: str = "/tmp/machine-storage"):
        self._base_path = base_path

    def _path(self, bucket: str, key: str) -> str:
        return os.path.join(self._base_path, bucket, key)

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def get(self, bucket: str, key: str) -> StorageObject:
        path = self._path(bucket, key)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{bucket}/{key} not found")
        with open(path, "rb") as f:
            data = f.read()
        return StorageObject(key=key, data=data, size=len(data))

    async def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> StorageObject:
        path = self._path(bucket, key)
        self._ensure_dir(path)
        with open(path, "wb") as f:
            f.write(data)
        return StorageObject(
            key=key, data=data, content_type=content_type, metadata=metadata or {}
        )

    async def delete(self, bucket: str, key: str) -> bool:
        path = self._path(bucket, key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def list(self, bucket: str, prefix: str = "") -> list[str]:
        bucket_path = os.path.join(self._base_path, bucket)
        if not os.path.exists(bucket_path):
            return []
        results = []
        for root, _, files in os.walk(bucket_path):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), bucket_path)
                if rel.startswith(prefix):
                    results.append(rel)
        return sorted(results)


# --- S3 Storage Backend ---


def _is_not_found(exc: BaseException) -> bool:
    """Best-effort detection of an S3-style "object/bucket missing" error."""
    if isinstance(exc, FileNotFoundError):
        return True
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = str((response.get("Error") or {}).get("Code", ""))
        if code in {"NoSuchKey", "NoSuchBucket", "404", "NotFound"}:
            return True
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
            return True
    return False


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend using ``boto3`` (lazily imported).

    ``boto3`` is only imported on first use, so registering the backend never
    requires the dependency. When it is absent a clear ``ImportError`` is raised
    from the offending operation.
    """

    def __init__(
        self,
        bucket_name: str = "default",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        self._bucket_name = bucket_name
        self._region = region
        self._endpoint_url = endpoint_url
        self._client = None

    def _bucket(self, bucket: str | None) -> str:
        return bucket or self._bucket_name

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError as e:
                raise ImportError(
                    "boto3 is required for S3StorageBackend. Install it with: "
                    "pip install boto3."
                ) from e
            self._client = boto3.client(
                "s3",
                region_name=self._region,
                endpoint_url=self._endpoint_url,
            )
        return self._client

    async def get(self, bucket: str, key: str) -> StorageObject:
        client = self._get_client()
        bucket = self._bucket(bucket)
        try:
            response = await asyncio.to_thread(
                client.get_object, Bucket=bucket, Key=key
            )
        except Exception as e:
            if _is_not_found(e):
                raise FileNotFoundError(f"s3://{bucket}/{key} not found") from e
            raise
        data = await asyncio.to_thread(response["Body"].read)
        return StorageObject(
            key=key,
            data=data,
            content_type=response.get("ContentType", "application/octet-stream"),
            metadata=response.get("Metadata", {}) or {},
            size=len(data),
        )

    async def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> StorageObject:
        client = self._get_client()
        bucket = self._bucket(bucket)
        await asyncio.to_thread(
            client.put_object,
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata=metadata or {},
        )
        return StorageObject(
            key=key, data=data, content_type=content_type, metadata=metadata or {}
        )

    async def delete(self, bucket: str, key: str) -> bool:
        client = self._get_client()
        bucket = self._bucket(bucket)
        try:
            await asyncio.to_thread(client.head_object, Bucket=bucket, Key=key)
        except Exception as e:
            if _is_not_found(e):
                return False
            raise
        await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=key)
        return True

    async def list(self, bucket: str, prefix: str = "") -> list[str]:
        client = self._get_client()
        bucket = self._bucket(bucket)
        response = await asyncio.to_thread(
            client.list_objects_v2, Bucket=bucket, Prefix=prefix
        )
        contents = response.get("Contents") or []
        return sorted(item["Key"] for item in contents)


# --- Plugin ---


class StorageSupportPlugin:
    """Plugin that registers storage backend implementations."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx):
        # storage-backend category already registered by memory_support
        ctx.register("storage-backend", "local", LocalStorageBackend())
        ctx.register("storage-backend", "s3", S3StorageBackend())

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
