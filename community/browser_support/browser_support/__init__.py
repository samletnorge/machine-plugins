"""browser_support: Browser automation category with Playwright and Stagehand backends."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

from .base import (
    BaseBrowser,
    BrowserResult,
    NavigateResult,
    ScreenshotResult,
    ElementResult,
)
from .playwright_browser import PlaywrightBrowser

__all__ = [
    "BrowserSupportPlugin",
    "BaseBrowser",
    "BrowserResult",
    "NavigateResult",
    "ScreenshotResult",
    "ElementResult",
    "PlaywrightBrowser",
]


class BrowserSupportPlugin:
    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category(
            "browser",
            operations={
                "navigate": {"method": "POST", "on": "item"},
                "screenshot": {"method": "POST", "on": "item"},
                "execute": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        # Construction is cheap and lazy — no browser is launched here.
        # PlaywrightBrowser.create() starts Playwright on first use and
        # raises a clear ImportError when the playwright package is absent.
        ctx.register("browser", "playwright", PlaywrightBrowser())

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
