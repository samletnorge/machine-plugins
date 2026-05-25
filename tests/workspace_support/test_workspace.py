"""Tests for AgentWorkspace — combines filesystem, sandbox, skills."""

import os
import tempfile
import pytest
from workspace_support.workspace import (
    AgentWorkspace,
    WorkspaceConfig,
)
from workspace_support.filesystem import LocalFileSystem
from workspace_support.sandbox import LocalSandbox
from workspace_support.skills import SkillsManager


SAMPLE_SKILL = """\
# Skill: test-skill

## Description
A test skill.

## When to Use
- Testing

## Instructions
Do test things.
"""


@pytest.fixture
def workspace_dir():
    d = tempfile.mkdtemp(prefix="machine_ws_test_")
    skills_dir = os.path.join(d, "skills")
    os.makedirs(skills_dir)
    with open(os.path.join(skills_dir, "test.md"), "w") as f:
        f.write(SAMPLE_SKILL)
    yield d
    import shutil

    shutil.rmtree(d, ignore_errors=True)


def test_workspace_config_defaults():
    cfg = WorkspaceConfig(root_dir="/tmp/test")
    assert cfg.ephemeral is True
    assert cfg.skills_dir is None


def test_workspace_config_custom():
    cfg = WorkspaceConfig(
        root_dir="/tmp/test", ephemeral=False, skills_dir="/tmp/skills"
    )
    assert cfg.ephemeral is False


@pytest.mark.asyncio
async def test_workspace_create_with_defaults(workspace_dir):
    ws = AgentWorkspace.create(WorkspaceConfig(root_dir=workspace_dir, ephemeral=False))
    assert ws.filesystem is not None
    assert ws.sandbox is not None


@pytest.mark.asyncio
async def test_workspace_filesystem_operations(workspace_dir):
    ws = AgentWorkspace.create(WorkspaceConfig(root_dir=workspace_dir, ephemeral=False))
    await ws.filesystem.write("test.txt", b"hello workspace")
    content = await ws.filesystem.read("test.txt")
    assert content == b"hello workspace"


@pytest.mark.asyncio
async def test_workspace_sandbox_execution(workspace_dir):
    ws = AgentWorkspace.create(WorkspaceConfig(root_dir=workspace_dir, ephemeral=False))
    result = await ws.sandbox.execute("print(1 + 1)")
    assert result.success is True
    assert "2" in result.stdout


@pytest.mark.asyncio
async def test_workspace_skills_discovery(workspace_dir):
    ws = AgentWorkspace.create(
        WorkspaceConfig(
            root_dir=workspace_dir,
            ephemeral=False,
            skills_dir=os.path.join(workspace_dir, "skills"),
        )
    )
    assert ws.skills is not None
    names = ws.skills.list_names()
    assert "test-skill" in names


@pytest.mark.asyncio
async def test_workspace_skills_load(workspace_dir):
    ws = AgentWorkspace.create(
        WorkspaceConfig(
            root_dir=workspace_dir,
            ephemeral=False,
            skills_dir=os.path.join(workspace_dir, "skills"),
        )
    )
    content = ws.skills.load("test-skill")
    assert "Do test things" in content


@pytest.mark.asyncio
async def test_workspace_ephemeral_cleanup(workspace_dir):
    ws = AgentWorkspace.create(WorkspaceConfig(root_dir=workspace_dir, ephemeral=True))
    await ws.filesystem.write("temp.txt", b"temp data")
    assert await ws.filesystem.exists("temp.txt") is True
    await ws.cleanup()


@pytest.mark.asyncio
async def test_workspace_context_manager(workspace_dir):
    async with AgentWorkspace.create(
        WorkspaceConfig(root_dir=workspace_dir, ephemeral=False)
    ) as ws:
        await ws.filesystem.write("ctx.txt", b"context manager works")
        content = await ws.filesystem.read("ctx.txt")
        assert content == b"context manager works"
