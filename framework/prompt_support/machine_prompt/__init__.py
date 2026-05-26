"""prompt_support: Defines the 'prompt' category with templates, rendering, and composition."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

HOOKSPECS = {
    "before_prompt_render": {"firstresult": False},
    "after_prompt_render": {"firstresult": False},
}


class PromptSupportPlugin:
    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category("prompt")
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
