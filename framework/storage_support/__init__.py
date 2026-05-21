"""Storage support plugin — registers storage backend implementations.

Uses existing 'storage-backend' category from memory_support.
Provides LocalStorageBackend and S3StorageBackend (mock).
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# --- Models ---


@dataclass
class StorageBucket:
    name: str
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


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


# --- S3 Storage Backend (Mock) ---


class S3StorageBackend(StorageBackend):
    """Mock S3-compatible storage (in-memory for testing)."""

    def __init__(
        self,
        bucket_name: str = "default",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        self._config = {
            "bucket": bucket_name,
            "region": region,
            "endpoint": endpoint_url,
        }
        self._store: dict[str, dict[str, StorageObject]] = {}

    async def get(self, bucket: str, key: str) -> StorageObject:
        b = self._store.get(bucket, {})
        obj = b.get(key)
        if not obj:
            raise FileNotFoundError(f"s3://{bucket}/{key} not found")
        return obj

    async def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> StorageObject:
        if bucket not in self._store:
            self._store[bucket] = {}
        obj = StorageObject(
            key=key, data=data, content_type=content_type, metadata=metadata or {}
        )
        self._store[bucket][key] = obj
        return obj

    async def delete(self, bucket: str, key: str) -> bool:
        b = self._store.get(bucket, {})
        if key in b:
            del b[key]
            return True
        return False

    async def list(self, bucket: str, prefix: str = "") -> list[str]:
        b = self._store.get(bucket, {})
        return sorted(k for k in b if k.startswith(prefix))


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
