"""Tests for PlaywrightBrowser (with mocked Playwright)."""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_playwright_navigate(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    result = await pw.navigate("https://example.com")
    assert result.success is True
    assert result.url == "https://example.com"
    assert result.title == "Test Page"
    mock_page.goto.assert_called_once_with(
        "https://example.com", wait_until="domcontentloaded"
    )


@pytest.mark.asyncio
async def test_playwright_click(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    result = await pw.click("button.submit")
    assert result.success is True
    mock_page.click.assert_called_once_with("button.submit")


@pytest.mark.asyncio
async def test_playwright_fill(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    result = await pw.fill("input#email", "test@example.com")
    assert result.success is True
    mock_page.fill.assert_called_once_with("input#email", "test@example.com")


@pytest.mark.asyncio
async def test_playwright_screenshot(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    result = await pw.screenshot()
    assert result.success is True
    assert result.image_bytes == b"\x89PNG_fake"
    assert result.format == "png"


@pytest.mark.asyncio
async def test_playwright_get_text(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    result = await pw.get_text("h1")
    assert result.success is True
    assert result.text == "Hello World"


@pytest.mark.asyncio
async def test_playwright_evaluate(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    result = await pw.evaluate("document.title")
    assert result.success is True
    assert result.data == "eval_result"


@pytest.mark.asyncio
async def test_playwright_navigate_error(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()

    mock_page.goto.side_effect = Exception("Network error")
    result = await pw.navigate("https://bad.example.com")
    assert result.success is False
    assert "Network error" in result.error


@pytest.mark.asyncio
async def test_playwright_close(mock_pw_browser, mock_page):
    from browser_support.playwright_browser import (
        PlaywrightBrowser,
    )

    pw = PlaywrightBrowser.__new__(PlaywrightBrowser)
    pw._browser = mock_pw_browser
    pw._page = mock_page
    pw._context = AsyncMock()
    pw._playwright = None

    await pw.close()
    mock_pw_browser.close.assert_called_once()
