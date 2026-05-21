"""Studio-support plugin.

Provides a web UI for testing agents, tools, and workflows.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

__all__ = ["StudioSupportPlugin"]


class StudioSupportPlugin:
    """Plugin that provides the Studio web UI."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: "PluginContext"):
        pass

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
