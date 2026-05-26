"""vectorstore_support: Defines the 'vector_store' category."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .hooks import HOOKSPECS

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class VectorStoreSupportPlugin:
    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category(
            "vector_store",
            operations={
                "upsert": {"method": "POST", "on": "item"},
                "search": {"method": "POST", "on": "item"},
                "delete": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
