"""Tests for StagehandBrowser — AI-driven element selection."""

import pytest
from unittest.mock import AsyncMock


def _make_mock_stagehand(mock_page):
    """Helper to create a StagehandBrowser with mocked internals."""
    from machine_core.plugins.browser_support.stagehand_browser import StagehandBrowser

    sb = StagehandBrowser.__new__(StagehandBrowser)
    sb._inner_browser = AsyncMock()
    sb._inner_browser._page = mock_page
    sb._inner_browser.navigate = AsyncMock()
    sb._inner_browser.screenshot = AsyncMock()
    sb._inner_browser.evaluate = AsyncMock()
    sb._inner_browser.close = AsyncMock()
    sb._resolve_selector = AsyncMock()
    return sb


@pytest.mark.asyncio
async def test_stagehand_navigate_delegates(mock_page):
    from machine_core.plugins.browser_support.base import NavigateResult

    sb = _make_mock_stagehand(mock_page)
    sb._inner_browser.navigate.return_value = NavigateResult(
        success=True, url="https://example.com", title="Example"
    )

    result = await sb.navigate("https://example.com")
    assert result.success is True
    sb._inner_browser.navigate.assert_called_once_with("https://example.com")


@pytest.mark.asyncio
async def test_stagehand_click_resolves_natural_language(mock_page):
    from machine_core.plugins.browser_support.base import BrowserResult

    sb = _make_mock_stagehand(mock_page)
    sb._resolve_selector.return_value = "button.login-btn"

    mock_page.click = AsyncMock()
    result_inner = BrowserResult(success=True)

    sb._inner_browser.click = AsyncMock(return_value=result_inner)

    result = await sb.click("the login button")
    sb._resolve_selector.assert_called_once_with("the login button")
    sb._inner_browser.click.assert_called_once_with("button.login-btn")
    assert result.success is True


@pytest.mark.asyncio
async def test_stagehand_fill_resolves_natural_language(mock_page):
    from machine_core.plugins.browser_support.base import BrowserResult

    sb = _make_mock_stagehand(mock_page)
    sb._resolve_selector.return_value = "input#email"
    sb._inner_browser.fill = AsyncMock(return_value=BrowserResult(success=True))

    result = await sb.fill("the email input field", "user@test.com")
    sb._resolve_selector.assert_called_once_with("the email input field")
    sb._inner_browser.fill.assert_called_once_with("input#email", "user@test.com")
    assert result.success is True


@pytest.mark.asyncio
async def test_stagehand_get_text_resolves(mock_page):
    from machine_core.plugins.browser_support.base import ElementResult

    sb = _make_mock_stagehand(mock_page)
    sb._resolve_selector.return_value = "h1.page-title"
    sb._inner_browser.get_text = AsyncMock(
        return_value=ElementResult(
            success=True, text="Welcome", tag="h1", selector="h1.page-title"
        )
    )

    result = await sb.get_text("the main page heading")
    sb._resolve_selector.assert_called_once_with("the main page heading")
    assert result.text == "Welcome"


@pytest.mark.asyncio
async def test_stagehand_resolve_failure(mock_page):
    sb = _make_mock_stagehand(mock_page)
    sb._resolve_selector.side_effect = ValueError("Could not find matching element")

    result = await sb.click("a nonexistent thing")
    assert result.success is False
    assert "Could not find" in result.error
