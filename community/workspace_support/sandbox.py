"""Abstract sandbox for code execution with pluggable backends.

Provides Sandbox ABC and ExecutionResult. Implementations include
LocalSandbox (subprocess) and DockerSandbox (container-based).
"""

from __future__ import annotations

import asyncio
import io
import os
import shutil
import tarfile
import tempfile
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, computed_field
from loguru import logger


class ExecutionResult(BaseModel):
    """Result of executing code in a sandbox."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @computed_field
    @property
    def success(self) -> bool:
        """True if exit_code is 0 and did not time out."""
        return self.exit_code == 0 and not self.timed_out


class Sandbox(ABC):
    """Abstract sandbox for code execution."""

    @abstractmethod
    async def execute(
        self, code: str, language: str = "python", timeout: float = 30.0
    ) -> ExecutionResult: ...

    @abstractmethod
    async def upload(self, path: str, content: bytes) -> None: ...

    @abstractmethod
    async def download(self, path: str) -> bytes: ...

    @abstractmethod
    async def cleanup(self) -> None: ...

    async def __aenter__(self) -> Sandbox:
        return self

    async def __aexit__(self, *args) -> None:
        await self.cleanup()


class LocalSandbox(Sandbox):
    """Execute code in a subprocess with resource limits."""

    def __init__(self, work_dir: Optional[str] = None) -> None:
        self._work_dir = work_dir or tempfile.mkdtemp(prefix="machine_sandbox_")

    async def execute(
        self, code: str, language: str = "python", timeout: float = 30.0
    ) -> ExecutionResult:
        if language == "python":
            cmd = ["python", "-c", code]
        elif language == "bash":
            cmd = ["bash", "-c", code]
        else:
            return ExecutionResult(
                exit_code=1, stderr=f"Unsupported language: {language}"
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._work_dir,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return ExecutionResult(
                exit_code=proc.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ExecutionResult(exit_code=-1, timed_out=True)
        except Exception as e:
            logger.error(f"LocalSandbox execution error: {e}")
            return ExecutionResult(exit_code=1, stderr=str(e))

    async def upload(self, path: str, content: bytes) -> None:
        full_path = os.path.join(self._work_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(content)

    async def download(self, path: str) -> bytes:
        full_path = os.path.join(self._work_dir, path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found in sandbox: {path}")
        with open(full_path, "rb") as f:
            return f.read()

    async def cleanup(self) -> None:
        if os.path.isdir(self._work_dir):
            shutil.rmtree(self._work_dir, ignore_errors=True)
            logger.debug(f"LocalSandbox cleaned up: {self._work_dir}")


def _get_docker_client():
    """Lazy import docker client."""
    try:
        import docker

        return docker.from_env()
    except ImportError:
        raise ImportError(
            "docker is required for DockerSandbox. Install with: pip install docker"
        )


class DockerSandbox(Sandbox):
    """Execute code inside a Docker container."""

    def __init__(
        self,
        image: str = "python:3.12-slim",
        network_disabled: bool = True,
        mem_limit: str = "256m",
        cpu_period: int = 100000,
        cpu_quota: int = 50000,
    ) -> None:
        self._image = image
        self._network_disabled = network_disabled
        self._mem_limit = mem_limit
        self._cpu_period = cpu_period
        self._cpu_quota = cpu_quota
        self._container = None
        self._client = None

    def _ensure_container(self):
        if self._container is not None:
            return
        self._client = _get_docker_client()
        self._container = self._client.containers.run(
            self._image,
            command="sleep infinity",
            detach=True,
            network_disabled=self._network_disabled,
            mem_limit=self._mem_limit,
            cpu_period=self._cpu_period,
            cpu_quota=self._cpu_quota,
        )
        logger.debug(f"DockerSandbox container started: {self._container.short_id}")

    async def execute(
        self, code: str, language: str = "python", timeout: float = 30.0
    ) -> ExecutionResult:
        self._ensure_container()

        if language == "python":
            cmd = ["python", "-c", code]
        elif language == "bash":
            cmd = ["bash", "-c", code]
        else:
            return ExecutionResult(
                exit_code=1, stderr=f"Unsupported language: {language}"
            )

        try:
            exit_code, output = self._container.exec_run(cmd, demux=False)
            output_str = output.decode("utf-8", errors="replace") if output else ""

            if exit_code == 0:
                return ExecutionResult(exit_code=0, stdout=output_str)
            else:
                return ExecutionResult(exit_code=exit_code, stderr=output_str)
        except Exception as e:
            logger.error(f"DockerSandbox execution error: {e}")
            return ExecutionResult(exit_code=1, stderr=str(e))

    async def upload(self, path: str, content: bytes) -> None:
        self._ensure_container()

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=os.path.basename(path))
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        buf.seek(0)

        dest_dir = os.path.dirname(f"/workspace/{path}") or "/workspace"
        self._container.put_archive(dest_dir, buf.getvalue())

    async def download(self, path: str) -> bytes:
        self._ensure_container()

        try:
            chunks, stat = self._container.get_archive(f"/workspace/{path}")
            data = b"".join(chunks)
            buf = io.BytesIO(data)
            with tarfile.open(fileobj=buf) as tar:
                member = tar.getmembers()[0]
                f = tar.extractfile(member)
                if f is None:
                    raise FileNotFoundError(f"File not found: {path}")
                return f.read()
        except Exception as e:
            raise FileNotFoundError(f"Failed to download {path}: {e}")

    async def cleanup(self) -> None:
        if self._container:
            try:
                self._container.remove(force=True)
                logger.debug("DockerSandbox container removed")
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")
            self._container = None
