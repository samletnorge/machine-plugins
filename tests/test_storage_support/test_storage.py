"""Tests for storage_support plugin."""

import os
import shutil
import sys
import types

import pytest

from storage_support import (
    StorageSupportPlugin,
    LocalStorageBackend,
    S3StorageBackend,
    StorageObject,
)

TEST_PATH = "/tmp/machine-storage-test"


@pytest.fixture
def local_backend():
    backend = LocalStorageBackend(base_path=TEST_PATH)
    yield backend
    if os.path.exists(TEST_PATH):
        shutil.rmtree(TEST_PATH)


class _FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeClientError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {
                "HTTPStatusCode": 404 if code in ("NoSuchKey", "404") else 500
            },
        }


class _FakeS3Client:
    """Minimal in-memory stand-in for the boto3 S3 client."""

    def __init__(self):
        self.objects: dict[tuple[str, str], tuple[bytes, str, dict]] = {}

    def put_object(
        self,
        Bucket,
        Key,
        Body,
        ContentType="application/octet-stream",
        Metadata=None,
    ):
        self.objects[(Bucket, Key)] = (Body, ContentType, Metadata or {})

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise _FakeClientError("NoSuchKey")
        data, content_type, metadata = self.objects[(Bucket, Key)]
        return {
            "Body": _FakeBody(data),
            "ContentType": content_type,
            "Metadata": metadata,
        }

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise _FakeClientError("404")
        return {}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)
        return {}

    def list_objects_v2(self, Bucket, Prefix=""):
        keys = sorted(
            k for (b, k) in self.objects if b == Bucket and k.startswith(Prefix)
        )
        if not keys:
            return {}
        return {"Contents": [{"Key": k} for k in keys]}


@pytest.fixture
def s3_backend(monkeypatch):
    fake_boto3 = types.ModuleType("boto3")
    client = _FakeS3Client()
    fake_boto3.client = lambda *args, **kwargs: client
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    return S3StorageBackend(bucket_name="mybucket")


# --- Local Storage tests ---


@pytest.mark.asyncio
async def test_local_put_and_get(local_backend):
    await local_backend.put("bucket1", "file.txt", b"hello world")
    obj = await local_backend.get("bucket1", "file.txt")
    assert obj.data == b"hello world"
    assert obj.key == "file.txt"


@pytest.mark.asyncio
async def test_local_get_missing(local_backend):
    with pytest.raises(FileNotFoundError):
        await local_backend.get("bucket1", "nope.txt")


@pytest.mark.asyncio
async def test_local_delete(local_backend):
    await local_backend.put("b", "f.txt", b"data")
    assert await local_backend.delete("b", "f.txt")
    assert not await local_backend.delete("b", "f.txt")


@pytest.mark.asyncio
async def test_local_list(local_backend):
    await local_backend.put("b", "a.txt", b"1")
    await local_backend.put("b", "b.txt", b"2")
    await local_backend.put("b", "sub/c.txt", b"3")
    keys = await local_backend.list("b")
    assert "a.txt" in keys
    assert "b.txt" in keys
    assert "sub/c.txt" in keys


@pytest.mark.asyncio
async def test_local_list_prefix(local_backend):
    await local_backend.put("b", "docs/a.txt", b"1")
    await local_backend.put("b", "docs/b.txt", b"2")
    await local_backend.put("b", "other.txt", b"3")
    keys = await local_backend.list("b", prefix="docs/")
    assert len(keys) == 2


# --- S3 Storage tests ---


@pytest.mark.asyncio
async def test_s3_put_and_get(s3_backend):
    await s3_backend.put("mybucket", "key1", b"data")
    obj = await s3_backend.get("mybucket", "key1")
    assert obj.data == b"data"


@pytest.mark.asyncio
async def test_s3_get_missing(s3_backend):
    with pytest.raises(FileNotFoundError):
        await s3_backend.get("mybucket", "nope")


@pytest.mark.asyncio
async def test_s3_delete(s3_backend):
    await s3_backend.put("b", "k", b"d")
    assert await s3_backend.delete("b", "k")
    assert not await s3_backend.delete("b", "k")


@pytest.mark.asyncio
async def test_s3_list(s3_backend):
    await s3_backend.put("b", "a", b"1")
    await s3_backend.put("b", "b", b"2")
    keys = await s3_backend.list("b")
    assert keys == ["a", "b"]


@pytest.mark.asyncio
async def test_s3_list_prefix(s3_backend):
    await s3_backend.put("b", "docs/a", b"1")
    await s3_backend.put("b", "docs/b", b"2")
    await s3_backend.put("b", "other", b"3")
    assert await s3_backend.list("b", prefix="docs/") == ["docs/a", "docs/b"]


@pytest.mark.asyncio
async def test_s3_uses_configured_bucket(s3_backend):
    await s3_backend.put("", "key", b"data")
    obj = await s3_backend.get("", "key")
    assert obj.data == b"data"


@pytest.mark.asyncio
async def test_s3_missing_boto3_raises_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", None)
    backend = S3StorageBackend()
    with pytest.raises(ImportError):
        await backend.put("b", "k", b"d")


# --- Model tests ---


def test_storage_object_auto_size():
    obj = StorageObject(key="k", data=b"hello")
    assert obj.size == 5


# --- Plugin test ---


def test_plugin_instantiation():
    plugin = StorageSupportPlugin()
    assert hasattr(plugin, "setup")
