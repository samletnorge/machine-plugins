"""Tests for Sandbox ABC and ExecutionResult."""

import os
import pytest
from unittest.mock import MagicMock, patch
from workspace_support.sandbox import (
    Sandbox,
    ExecutionResult,
    LocalSandbox,
    DockerSandbox,
)


def test_execution_result_success():
    r = ExecutionResult(exit_code=0, stdout="hello\n", stderr="")
    assert r.exit_code == 0
    assert r.stdout == "hello\n"
    assert r.success is True


def test_execution_result_failure():
    r = ExecutionResult(exit_code=1, stdout="", stderr="NameError")
    assert r.success is False
    assert r.stderr == "NameError"


def test_execution_result_timeout():
    r = ExecutionResult(exit_code=-1, stdout="", stderr="", timed_out=True)
    assert r.timed_out is True
    assert r.success is False


def test_sandbox_is_abstract():
    with pytest.raises(TypeError):
        Sandbox()


@pytest.mark.asyncio
async def test_local_sandbox_execute_python():
    async with LocalSandbox() as sb:
        result = await sb.execute("print('hello from sandbox')")
        assert result.success is True
        assert "hello from sandbox" in result.stdout


@pytest.mark.asyncio
async def test_local_sandbox_execute_error():
    async with LocalSandbox() as sb:
        result = await sb.execute("raise ValueError('boom')")
        assert result.success is False
        assert result.exit_code != 0
        assert "ValueError" in result.stderr


@pytest.mark.asyncio
async def test_local_sandbox_execute_timeout():
    async with LocalSandbox() as sb:
        result = await sb.execute("import time; time.sleep(10)", timeout=0.5)
        assert result.timed_out is True
        assert result.success is False


@pytest.mark.asyncio
async def test_local_sandbox_execute_bash():
    async with LocalSandbox() as sb:
        result = await sb.execute("echo 'bash works'", language="bash")
        assert result.success is True
        assert "bash works" in result.stdout


@pytest.mark.asyncio
async def test_local_sandbox_upload_and_download():
    async with LocalSandbox() as sb:
        await sb.upload("test.txt", b"hello world")
        content = await sb.download("test.txt")
        assert content == b"hello world"


@pytest.mark.asyncio
async def test_local_sandbox_download_missing():
    async with LocalSandbox() as sb:
        with pytest.raises(FileNotFoundError):
            await sb.download("nonexistent.txt")


@pytest.mark.asyncio
async def test_local_sandbox_cleanup_removes_tempdir():
    sb = LocalSandbox()
    work_dir = sb._work_dir
    assert os.path.isdir(work_dir)
    await sb.cleanup()
    assert not os.path.isdir(work_dir)


@pytest.mark.asyncio
async def test_docker_sandbox_execute_python():
    mock_container = MagicMock()
    mock_container.exec_run = MagicMock(return_value=(0, b"hello from docker\n"))
    mock_container.remove = MagicMock()

    mock_client = MagicMock()
    mock_client.containers.run = MagicMock(return_value=mock_container)

    with patch(
        "workspace_support.sandbox._get_docker_client",
        return_value=mock_client,
    ):
        sb = DockerSandbox(image="python:3.12-slim")
        result = await sb.execute("print('hello from docker')")
        assert result.success is True
        assert "hello from docker" in result.stdout


@pytest.mark.asyncio
async def test_docker_sandbox_execute_error():
    mock_container = MagicMock()
    mock_container.exec_run = MagicMock(
        return_value=(1, b"NameError: name 'x' is not defined\n")
    )
    mock_container.remove = MagicMock()

    mock_client = MagicMock()
    mock_client.containers.run = MagicMock(return_value=mock_container)

    with patch(
        "workspace_support.sandbox._get_docker_client",
        return_value=mock_client,
    ):
        sb = DockerSandbox(image="python:3.12-slim")
        result = await sb.execute("print(x)")
        assert result.success is False
        assert "NameError" in result.stderr


@pytest.mark.asyncio
async def test_docker_sandbox_upload():
    mock_container = MagicMock()
    mock_container.put_archive = MagicMock()
    mock_container.remove = MagicMock()

    mock_client = MagicMock()
    mock_client.containers.run = MagicMock(return_value=mock_container)

    with patch(
        "workspace_support.sandbox._get_docker_client",
        return_value=mock_client,
    ):
        sb = DockerSandbox(image="python:3.12-slim")
        sb._container = mock_container
        await sb.upload("test.txt", b"hello world")
        mock_container.put_archive.assert_called_once()


@pytest.mark.asyncio
async def test_docker_sandbox_cleanup():
    mock_container = MagicMock()
    mock_container.remove = MagicMock()

    with patch("workspace_support.sandbox._get_docker_client"):
        sb = DockerSandbox(image="python:3.12-slim")
        sb._container = mock_container
        await sb.cleanup()
        mock_container.remove.assert_called_once_with(force=True)
