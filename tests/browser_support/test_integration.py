"""Integration test: browser tools + workspace together."""

import tempfile
import pytest
from unittest.mock import AsyncMock

from machine_core.plugins.browser_support.base import (
    NavigateResult,
    ScreenshotResult,
)
from machine_core.plugins.browser_support.tools import (
    create_browser_tools,
    ScreenshotInput,
)
from machine_core.plugins.workspace_support.workspace import (
    AgentWorkspace,
    WorkspaceConfig,
)


@pytest.mark.asyncio
async def test_browser_screenshot_saved_to_workspace():
    """Agent takes a screenshot and saves it to workspace filesystem."""
    mock_browser = AsyncMock()
    mock_browser.screenshot = AsyncMock(
        return_value=ScreenshotResult(
            success=True, image_bytes=b"\x89PNG_fake_img", format="png"
        )
    )
    mock_browser.navigate = AsyncMock(
        return_value=NavigateResult(
            success=True, url="https://example.com", title="Example"
        )
    )

    tools = create_browser_tools(mock_browser)
    ss_tool = next(t for t in tools if t.name == "browser_screenshot")

    ws_dir = tempfile.mkdtemp(prefix="machine_integ_")
    try:
        ws = AgentWorkspace.create(WorkspaceConfig(root_dir=ws_dir, ephemeral=False))

        result = await ss_tool.execute(ScreenshotInput())
        assert result["success"] is True

        await ws.filesystem.write(
            "screenshot.png", mock_browser.screenshot.return_value.image_bytes
        )
        content = await ws.filesystem.read("screenshot.png")
        assert content == b"\x89PNG_fake_img"
    finally:
        import shutil

        shutil.rmtree(ws_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_workspace_execute_and_save():
    """Agent executes code in sandbox and saves output to filesystem."""
    ws_dir = tempfile.mkdtemp(prefix="machine_integ2_")
    try:
        ws = AgentWorkspace.create(WorkspaceConfig(root_dir=ws_dir, ephemeral=False))

        result = await ws.sandbox.execute("print('computed result: 42')")
        assert result.success is True

        await ws.filesystem.write("output.txt", result.stdout.encode())
        content = await ws.filesystem.read("output.txt")
        assert b"computed result: 42" in content
    finally:
        import shutil

        shutil.rmtree(ws_dir, ignore_errors=True)
