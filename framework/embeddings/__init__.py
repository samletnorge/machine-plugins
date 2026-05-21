"""embeddings: Defines the 'embedding' category for text-to-vector providers."""

from __future__ import annotations
from typing import TYPE_CHECKING
from .hooks import HOOKSPECS

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class EmbeddingsPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category("embedding")
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs):
        pass
