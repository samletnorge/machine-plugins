"""Abstract base browser and result types.

All browser implementations (Playwright, Stagehand, etc.) implement
the BaseBrowser ABC. Result types use pydantic for validation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class BrowserResult(BaseModel):
    """Generic result from a browser operation."""

    success: bool
    data: Any = None
    error: Optional[str] = None


class NavigateResult(BrowserResult):
    """Result of navigating to a URL."""

    url: str = ""
    title: str = ""


class ScreenshotResult(BrowserResult):
    """Result of taking a screenshot."""

    image_bytes: bytes = b""
    format: str = "png"


class ElementResult(BrowserResult):
    """Result of reading an element."""

    text: str = ""
    tag: str = ""
    selector: str = ""


# ---------------------------------------------------------------------------
# Abstract base browser
# ---------------------------------------------------------------------------


class BaseBrowser(ABC):
    """Abstract browser interface.

    All browser implementations must provide these methods.
    Methods are async to support non-blocking I/O.
    """

    @abstractmethod
    async def navigate(self, url: str) -> NavigateResult:
        """Navigate to a URL. Returns page URL and title."""
        ...

    @abstractmethod
    async def click(self, selector: str) -> BrowserResult:
        """Click an element identified by selector."""
        ...

    @abstractmethod
    async def fill(self, selector: str, value: str) -> BrowserResult:
        """Fill a form field with a value."""
        ...

    @abstractmethod
    async def screenshot(self) -> ScreenshotResult:
        """Take a screenshot of the current page."""
        ...

    @abstractmethod
    async def get_text(self, selector: str) -> ElementResult:
        """Get the text content of an element."""
        ...

    @abstractmethod
    async def evaluate(self, js: str) -> BrowserResult:
        """Evaluate JavaScript on the page and return the result."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the browser and clean up resources."""
        ...

    async def __aenter__(self) -> BaseBrowser:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
