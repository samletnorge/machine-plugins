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

__all__ = [
    "BrowserSupportPlugin",
    "BaseBrowser",
    "BrowserResult",
    "NavigateResult",
    "ScreenshotResult",
    "ElementResult",
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

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
