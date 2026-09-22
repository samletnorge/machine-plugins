"""Abstract filesystem with pluggable backends.

Provides FileSystem ABC for file operations. LocalFileSystem stores
files on the local disk, scoped to a root directory with path traversal protection.
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod

from pydantic import BaseModel
from loguru import logger


class FileInfo(BaseModel):
    """Metadata about a file or directory."""

    path: str
    size: int = 0
    is_dir: bool = False


class FileSystem(ABC):
    """Abstract filesystem interface."""

    @abstractmethod
    async def read(self, path: str) -> bytes: ...

    @abstractmethod
    async def write(self, path: str, content: bytes) -> None: ...

    @abstractmethod
    async def list(self, path: str) -> list[FileInfo]: ...

    @abstractmethod
    async def delete(self, path: str) -> None: ...

    @abstractmethod
    async def exists(self, path: str) -> bool: ...


class LocalFileSystem(FileSystem):
    """File operations on the local disk, scoped to a root directory."""

    def __init__(self, root: str) -> None:
        self._root = os.path.abspath(root)

    def _resolve(self, path: str) -> str:
        full = os.path.normpath(os.path.join(self._root, path))
        if not full.startswith(self._root):
            raise ValueError(f"Path '{path}' resolves outside root directory")
        return full

    async def read(self, path: str) -> bytes:
        full = self._resolve(path)
        if not os.path.isfile(full):
            raise FileNotFoundError(f"File not found: {path}")
        with open(full, "rb") as f:
            return f.read()

    async def write(self, path: str, content: bytes) -> None:
        full = self._resolve(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(content)

    async def list(self, path: str) -> list[FileInfo]:
        full = self._resolve(path)
        if not os.path.isdir(full):
            return []
        entries = []
        for name in sorted(os.listdir(full)):
            entry_path = os.path.join(full, name)
            is_dir = os.path.isdir(entry_path)
            size = os.path.getsize(entry_path) if not is_dir else 0
            entries.append(FileInfo(path=name, size=size, is_dir=is_dir))
        return entries

    async def delete(self, path: str) -> None:
        full = self._resolve(path)
        if os.path.isfile(full):
            os.remove(full)
        elif os.path.isdir(full):
            shutil.rmtree(full)

    async def exists(self, path: str) -> bool:
        full = self._resolve(path)
        return os.path.exists(full)
