"""Expose browser operations as tool definitions for agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from .base import BaseBrowser


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class BrowseInput(BaseModel):
    """Input for browser navigation."""

    url: str


class ClickInput(BaseModel):
    """Input for clicking an element."""

    selector: str


class FillInput(BaseModel):
    """Input for filling a form field."""

    selector: str
    value: str


class ScreenshotInput(BaseModel):
    """Input for taking a screenshot."""

    pass


class GetTextInput(BaseModel):
    """Input for getting element text."""

    selector: str


class EvalInput(BaseModel):
    """Input for evaluating JavaScript."""

    js: str


# ---------------------------------------------------------------------------
# Simple tool wrapper
# ---------------------------------------------------------------------------


@dataclass
class BrowserTool:
    """Lightweight tool wrapper for browser operations."""

    name: str
    description: str
    execute: Any  # async callable(input) -> dict


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def create_browser_tools(browser: BaseBrowser) -> list[BrowserTool]:
    """Create BrowserTool instances that wrap browser operations."""

    async def _navigate(input: BrowseInput) -> dict:
        result = await browser.navigate(input.url)
        return {
            "success": result.success,
            "url": result.url,
            "title": result.title,
            "error": result.error,
        }

    async def _click(input: ClickInput) -> dict:
        result = await browser.click(input.selector)
        return {"success": result.success, "error": result.error}

    async def _fill(input: FillInput) -> dict:
        result = await browser.fill(input.selector, input.value)
        return {"success": result.success, "error": result.error}

    async def _screenshot(input: ScreenshotInput) -> dict:
        result = await browser.screenshot()
        return {
            "success": result.success,
            "format": result.format,
            "size_bytes": len(result.image_bytes),
            "error": result.error,
        }

    async def _get_text(input: GetTextInput) -> dict:
        result = await browser.get_text(input.selector)
        return {
            "success": result.success,
            "text": result.text,
            "tag": result.tag,
            "error": result.error,
        }

    async def _evaluate(input: EvalInput) -> dict:
        result = await browser.evaluate(input.js)
        return {"success": result.success, "data": result.data, "error": result.error}

    return [
        BrowserTool(
            name="browser_navigate",
            description="Navigate to a URL in the browser.",
            execute=_navigate,
        ),
        BrowserTool(
            name="browser_click",
            description="Click an element by CSS selector or natural language description.",
            execute=_click,
        ),
        BrowserTool(
            name="browser_fill",
            description="Fill a form field with a value.",
            execute=_fill,
        ),
        BrowserTool(
            name="browser_screenshot",
            description="Take a screenshot of the current page.",
            execute=_screenshot,
        ),
        BrowserTool(
            name="browser_get_text",
            description="Get the text content of an element.",
            execute=_get_text,
        ),
        BrowserTool(
            name="browser_evaluate",
            description="Evaluate JavaScript on the current page.",
            execute=_evaluate,
        ),
    ]
