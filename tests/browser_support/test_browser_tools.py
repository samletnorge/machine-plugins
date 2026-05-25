"""Tests for browser-as-tool — agents can use the browser."""

import pytest
from unittest.mock import AsyncMock
from browser_support.tools import (
    create_browser_tools,
    BrowseInput,
    ClickInput,
    FillInput,
    ScreenshotInput,
    GetTextInput,
    EvalInput,
)
from browser_support.base import (
    BrowserResult,
    NavigateResult,
    ScreenshotResult,
    ElementResult,
)


@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    browser.navigate = AsyncMock(
        return_value=NavigateResult(
            success=True, url="https://example.com", title="Example"
        )
    )
    browser.click = AsyncMock(return_value=BrowserResult(success=True))
    browser.fill = AsyncMock(return_value=BrowserResult(success=True))
    browser.screenshot = AsyncMock(
        return_value=ScreenshotResult(success=True, image_bytes=b"img", format="png")
    )
    browser.get_text = AsyncMock(
        return_value=ElementResult(success=True, text="Hello", tag="h1", selector="h1")
    )
    browser.evaluate = AsyncMock(
        return_value=BrowserResult(success=True, data="result")
    )
    return browser


def test_create_browser_tools_returns_six_tools(mock_browser):
    tools = create_browser_tools(mock_browser)
    assert len(tools) == 6
    names = {t.name for t in tools}
    assert names == {
        "browser_navigate",
        "browser_click",
        "browser_fill",
        "browser_screenshot",
        "browser_get_text",
        "browser_evaluate",
    }


@pytest.mark.asyncio
async def test_browser_navigate_tool(mock_browser):
    tools = create_browser_tools(mock_browser)
    nav_tool = next(t for t in tools if t.name == "browser_navigate")
    result = await nav_tool.execute(BrowseInput(url="https://example.com"))
    assert result["success"] is True
    assert result["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_browser_click_tool(mock_browser):
    tools = create_browser_tools(mock_browser)
    click_tool = next(t for t in tools if t.name == "browser_click")
    result = await click_tool.execute(ClickInput(selector="button"))
    assert result["success"] is True


@pytest.mark.asyncio
async def test_browser_fill_tool(mock_browser):
    tools = create_browser_tools(mock_browser)
    fill_tool = next(t for t in tools if t.name == "browser_fill")
    result = await fill_tool.execute(FillInput(selector="input", value="hello"))
    assert result["success"] is True


@pytest.mark.asyncio
async def test_browser_screenshot_tool(mock_browser):
    tools = create_browser_tools(mock_browser)
    ss_tool = next(t for t in tools if t.name == "browser_screenshot")
    result = await ss_tool.execute(ScreenshotInput())
    assert result["success"] is True
    assert result["format"] == "png"


@pytest.mark.asyncio
async def test_browser_get_text_tool(mock_browser):
    tools = create_browser_tools(mock_browser)
    gt_tool = next(t for t in tools if t.name == "browser_get_text")
    result = await gt_tool.execute(GetTextInput(selector="h1"))
    assert result["text"] == "Hello"
