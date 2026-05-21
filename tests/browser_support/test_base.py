"""Tests for BaseBrowser ABC and result types."""

import pytest
from machine_core.plugins.browser_support.base import (
    BaseBrowser,
    BrowserResult,
    NavigateResult,
    ScreenshotResult,
    ElementResult,
)


def test_browser_result_success():
    r = BrowserResult(success=True, data="hello")
    assert r.success is True
    assert r.data == "hello"
    assert r.error is None


def test_browser_result_failure():
    r = BrowserResult(success=False, error="timeout")
    assert r.success is False
    assert r.error == "timeout"
    assert r.data is None


def test_navigate_result():
    r = NavigateResult(success=True, url="https://example.com", title="Example")
    assert r.url == "https://example.com"
    assert r.title == "Example"


def test_screenshot_result():
    r = ScreenshotResult(success=True, image_bytes=b"\x89PNG", format="png")
    assert r.image_bytes == b"\x89PNG"
    assert r.format == "png"


def test_element_result():
    r = ElementResult(
        success=True, text="Click me", tag="button", selector="button.primary"
    )
    assert r.text == "Click me"
    assert r.tag == "button"


def test_base_browser_is_abstract():
    """BaseBrowser cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseBrowser()


class _ConcreteBrowser(BaseBrowser):
    """Minimal concrete implementation for testing the ABC contract."""

    async def navigate(self, url: str) -> NavigateResult:
        return NavigateResult(success=True, url=url, title="Test")

    async def click(self, selector: str) -> BrowserResult:
        return BrowserResult(success=True)

    async def fill(self, selector: str, value: str) -> BrowserResult:
        return BrowserResult(success=True)

    async def screenshot(self) -> ScreenshotResult:
        return ScreenshotResult(success=True, image_bytes=b"img", format="png")

    async def get_text(self, selector: str) -> ElementResult:
        return ElementResult(success=True, text="text", tag="div", selector=selector)

    async def evaluate(self, js: str) -> BrowserResult:
        return BrowserResult(success=True, data="result")

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_concrete_browser_navigate():
    b = _ConcreteBrowser()
    result = await b.navigate("https://example.com")
    assert result.success is True
    assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_concrete_browser_click():
    b = _ConcreteBrowser()
    result = await b.click("button.submit")
    assert result.success is True


@pytest.mark.asyncio
async def test_concrete_browser_fill():
    b = _ConcreteBrowser()
    result = await b.fill("input#email", "user@test.com")
    assert result.success is True


@pytest.mark.asyncio
async def test_concrete_browser_screenshot():
    b = _ConcreteBrowser()
    result = await b.screenshot()
    assert result.image_bytes == b"img"


@pytest.mark.asyncio
async def test_concrete_browser_get_text():
    b = _ConcreteBrowser()
    result = await b.get_text("h1")
    assert result.text == "text"


@pytest.mark.asyncio
async def test_concrete_browser_evaluate():
    b = _ConcreteBrowser()
    result = await b.evaluate("document.title")
    assert result.data == "result"
