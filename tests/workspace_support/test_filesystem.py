"""Tests for FileSystem ABC and LocalFileSystem."""

import os
import tempfile
import pytest
from workspace_support.filesystem import (
    FileSystem,
    LocalFileSystem,
    FileInfo,
)


def test_file_info():
    fi = FileInfo(path="test.txt", size=100, is_dir=False)
    assert fi.path == "test.txt"
    assert fi.size == 100
    assert fi.is_dir is False


def test_filesystem_is_abstract():
    with pytest.raises(TypeError):
        FileSystem()


@pytest.fixture
def local_fs():
    root = tempfile.mkdtemp(prefix="machine_fs_test_")
    fs = LocalFileSystem(root=root)
    yield fs
    import shutil

    shutil.rmtree(root, ignore_errors=True)


@pytest.mark.asyncio
async def test_local_write_and_read(local_fs):
    await local_fs.write("hello.txt", b"hello world")
    content = await local_fs.read("hello.txt")
    assert content == b"hello world"


@pytest.mark.asyncio
async def test_local_exists(local_fs):
    assert await local_fs.exists("nope.txt") is False
    await local_fs.write("yes.txt", b"data")
    assert await local_fs.exists("yes.txt") is True


@pytest.mark.asyncio
async def test_local_list(local_fs):
    await local_fs.write("a.txt", b"a")
    await local_fs.write("b.txt", b"b")
    files = await local_fs.list(".")
    names = {f.path for f in files}
    assert "a.txt" in names
    assert "b.txt" in names


@pytest.mark.asyncio
async def test_local_list_nested(local_fs):
    await local_fs.write("sub/c.txt", b"c")
    files = await local_fs.list("sub")
    assert len(files) == 1
    assert files[0].path == "c.txt"


@pytest.mark.asyncio
async def test_local_delete(local_fs):
    await local_fs.write("del.txt", b"gone")
    assert await local_fs.exists("del.txt") is True
    await local_fs.delete("del.txt")
    assert await local_fs.exists("del.txt") is False


@pytest.mark.asyncio
async def test_local_delete_nonexistent(local_fs):
    await local_fs.delete("nope.txt")  # Should not raise


@pytest.mark.asyncio
async def test_local_read_nonexistent(local_fs):
    with pytest.raises(FileNotFoundError):
        await local_fs.read("nope.txt")


@pytest.mark.asyncio
async def test_local_prevents_path_traversal(local_fs):
    with pytest.raises(ValueError, match="outside root"):
        await local_fs.write("../../etc/passwd", b"hack")
