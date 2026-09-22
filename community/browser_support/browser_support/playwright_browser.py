"""Playwright-based browser implementation.

Requires: pip install playwright && python -m playwright install
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from .base import (
    BaseBrowser,
    BrowserResult,
    NavigateResult,
    ScreenshotResult,
    ElementResult,
)

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False
    async_playwright = None  # type: ignore
    Browser = None  # type: ignore
    Page = None  # type: ignore
    BrowserContext = None  # type: ignore


class PlaywrightBrowser(BaseBrowser):
    """Browser automation via Playwright.

    Usage:
        browser = await PlaywrightBrowser.create(headless=True)
        result = await browser.navigate("https://example.com")
        await browser.close()

    Or as async context manager:
        async with await PlaywrightBrowser.create() as browser:
            await browser.navigate("https://example.com")
    """

    def __init__(self) -> None:
        # Private — use PlaywrightBrowser.create() instead
        self._playwright: Any = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @classmethod
    async def create(
        cls,
        headless: bool = True,
        browser_type: str = "chromium",
    ) -> PlaywrightBrowser:
        """Factory method to create and initialize a PlaywrightBrowser."""
        if not _HAS_PLAYWRIGHT:
            raise ImportError(
                "playwright is required for PlaywrightBrowser. "
                "Install with: pip install playwright && python -m playwright install"
            )
        instance = cls()
        instance._playwright = await async_playwright().start()

        launcher = getattr(instance._playwright, browser_type)
        instance._browser = await launcher.launch(headless=headless)
        instance._context = await instance._browser.new_context()
        instance._page = await instance._context.new_page()

        logger.debug(f"PlaywrightBrowser started ({browser_type}, headless={headless})")
        return instance

    async def navigate(self, url: str) -> NavigateResult:
        try:
            await self._page.goto(url, wait_until="domcontentloaded")
            title = await self._page.title()
            return NavigateResult(success=True, url=self._page.url, title=title)
        except Exception as e:
            logger.error(f"Navigation to {url} failed: {e}")
            return NavigateResult(success=False, error=str(e))

    async def click(self, selector: str) -> BrowserResult:
        try:
            await self._page.click(selector)
            return BrowserResult(success=True)
        except Exception as e:
            logger.error(f"Click on '{selector}' failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def fill(self, selector: str, value: str) -> BrowserResult:
        try:
            await self._page.fill(selector, value)
            return BrowserResult(success=True)
        except Exception as e:
            logger.error(f"Fill '{selector}' failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def screenshot(self) -> ScreenshotResult:
        try:
            image_bytes = await self._page.screenshot()
            return ScreenshotResult(success=True, image_bytes=image_bytes, format="png")
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ScreenshotResult(success=False, error=str(e))

    async def get_text(self, selector: str) -> ElementResult:
        try:
            element = await self._page.query_selector(selector)
            if element is None:
                return ElementResult(
                    success=False, error=f"Element '{selector}' not found"
                )
            text = await element.text_content() or ""
            tag = await element.evaluate("el => el.tagName.toLowerCase()")
            return ElementResult(success=True, text=text, tag=tag, selector=selector)
        except Exception as e:
            logger.error(f"get_text '{selector}' failed: {e}")
            return ElementResult(success=False, error=str(e))

    async def evaluate(self, js: str) -> BrowserResult:
        try:
            result = await self._page.evaluate(js)
            return BrowserResult(success=True, data=result)
        except Exception as e:
            logger.error(f"evaluate failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.debug("PlaywrightBrowser closed")
