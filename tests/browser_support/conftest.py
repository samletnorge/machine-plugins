"""Shared fixtures for browser tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_page():
    """A mock Playwright page object."""
    page = AsyncMock()
    page.goto = AsyncMock(return_value=None)
    page.title = AsyncMock(return_value="Test Page")
    page.url = "https://example.com"
    page.click = AsyncMock(return_value=None)
    page.fill = AsyncMock(return_value=None)
    page.screenshot = AsyncMock(return_value=b"\x89PNG_fake")
    page.evaluate = AsyncMock(return_value="eval_result")
    page.text_content = AsyncMock(return_value="Hello World")
    page.query_selector = AsyncMock()

    element = AsyncMock()
    element.text_content = AsyncMock(return_value="Hello World")
    element.evaluate = AsyncMock(return_value="div")
    page.query_selector.return_value = element

    return page


@pytest.fixture
def mock_browser_context(mock_page):
    """A mock Playwright browser context."""
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    context.close = AsyncMock()
    return context


@pytest.fixture
def mock_pw_browser(mock_browser_context):
    """A mock Playwright browser."""
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=mock_browser_context)
    browser.close = AsyncMock()
    return browser
