"""Tests for storage_support plugin."""

import os
import shutil
import pytest
from machine_core.plugins.storage_support import (
    StorageSupportPlugin,
    LocalStorageBackend,
    S3StorageBackend,
    StorageObject,
    StorageBucket,
)

TEST_PATH = "/tmp/machine-storage-test"


@pytest.fixture
def local_backend():
    backend = LocalStorageBackend(base_path=TEST_PATH)
    yield backend
    if os.path.exists(TEST_PATH):
        shutil.rmtree(TEST_PATH)


@pytest.fixture
def s3_backend():
    return S3StorageBackend()


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


# --- Model tests ---


def test_storage_object_auto_size():
    obj = StorageObject(key="k", data=b"hello")
    assert obj.size == 5


# --- Plugin test ---


def test_plugin_instantiation():
    plugin = StorageSupportPlugin()
    assert hasattr(plugin, "setup")
