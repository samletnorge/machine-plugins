"""agent-support: Defines the 'agent' category with schemas, handoff, and lifecycle hooks."""

from __future__ import annotations
from typing import TYPE_CHECKING
from .hooks import HOOKSPECS

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class AgentSupportPlugin:
    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category(
            "agent",
            operations={
                "run": {"method": "POST", "on": "item"},
                "stream": {"method": "POST", "on": "item"},
                "generate": {"method": "POST", "on": "item"},
            },
        )
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
