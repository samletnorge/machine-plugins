"""tool-support: Defines the 'tool' category with schemas, hooks, and @tool decorator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .hooks import HOOKSPECS

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class ToolSupportPlugin:
    """In-process plugin class for tool-support."""

    async def initialize(self, **kwargs):
        """Called by transport on load."""
        pass

    async def setup(self, ctx: PluginContext):
        """Register category, hookspecs, and events."""
        ctx.register_category(
            "tool",
            operations={
                "execute": {"method": "POST", "on": "item"},
            },
        )
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs):
        """Called on unload."""
        pass
