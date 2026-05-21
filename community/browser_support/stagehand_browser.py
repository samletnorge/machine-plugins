"""AI-driven browser that resolves natural language to CSS selectors.

Instead of requiring precise CSS selectors, StagehandBrowser accepts
natural language descriptions like "the login button" and uses an LLM
to find the matching element from a DOM snapshot.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from loguru import logger
from pydantic import BaseModel

from .base import (
    BaseBrowser,
    BrowserResult,
    NavigateResult,
    ScreenshotResult,
    ElementResult,
)


class SelectorResolution(BaseModel):
    """LLM's response when resolving a natural language description to a selector."""

    selector: str
    confidence: float = 1.0
    reasoning: str = ""


# Type for the LLM function: takes (description, dom_snapshot) -> SelectorResolution
SelectorResolver = Callable[[str, str], Awaitable[SelectorResolution]]


class StagehandBrowser(BaseBrowser):
    """Browser that uses an LLM to resolve element descriptions to selectors.

    Wraps an inner BaseBrowser (typically PlaywrightBrowser) and intercepts
    click/fill/get_text calls. If the selector looks like natural language
    (contains spaces, no CSS punctuation), it sends a DOM snapshot + the
    description to the LLM, which returns a CSS selector.
    """

    def __init__(
        self,
        inner_browser: BaseBrowser,
        resolve_fn: SelectorResolver,
    ) -> None:
        self._inner_browser = inner_browser
        self._resolve_fn = resolve_fn

    @staticmethod
    def _looks_like_natural_language(selector: str) -> bool:
        """Heuristic: if selector has spaces and no CSS-like chars, it's NL."""
        css_chars = {".", "#", "[", "]", ">", "~", "+", ":", "(", ")"}
        if " " in selector and not any(c in selector for c in css_chars):
            return True
        return False

    async def _resolve_selector(self, description: str) -> str:
        """Use the LLM to resolve a natural language description to a CSS selector."""
        dom_result = await self._inner_browser.evaluate(
            "document.documentElement.outerHTML.substring(0, 50000)"
        )
        dom_snapshot = str(dom_result.data) if dom_result.success else "<html></html>"

        resolution = await self._resolve_fn(description, dom_snapshot)
        logger.debug(
            f"Resolved '{description}' -> '{resolution.selector}' "
            f"(confidence={resolution.confidence})"
        )
        return resolution.selector

    async def _maybe_resolve(self, selector: str) -> str:
        """Resolve if it looks like natural language, otherwise pass through."""
        if self._looks_like_natural_language(selector):
            return await self._resolve_selector(selector)
        return selector

    async def navigate(self, url: str) -> NavigateResult:
        return await self._inner_browser.navigate(url)

    async def click(self, selector: str) -> BrowserResult:
        try:
            resolved = await self._maybe_resolve(selector)
            return await self._inner_browser.click(resolved)
        except Exception as e:
            logger.error(f"StagehandBrowser click failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def fill(self, selector: str, value: str) -> BrowserResult:
        try:
            resolved = await self._maybe_resolve(selector)
            return await self._inner_browser.fill(resolved, value)
        except Exception as e:
            logger.error(f"StagehandBrowser fill failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def screenshot(self) -> ScreenshotResult:
        return await self._inner_browser.screenshot()

    async def get_text(self, selector: str) -> ElementResult:
        try:
            resolved = await self._maybe_resolve(selector)
            return await self._inner_browser.get_text(resolved)
        except Exception as e:
            logger.error(f"StagehandBrowser get_text failed: {e}")
            return ElementResult(success=False, error=str(e))

    async def evaluate(self, js: str) -> BrowserResult:
        return await self._inner_browser.evaluate(js)

    async def close(self) -> None:
        await self._inner_browser.close()
