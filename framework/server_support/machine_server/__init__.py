"""server-support: Auto-generates FastAPI HTTP endpoints from Machine registry."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

HOOKSPECS: dict[str, dict[str, Any]] = {
    "hooks/beforeServerStart": {"firstresult": False},
    "hooks/afterServerStart": {"firstresult": False},
    "hooks/beforeRequest": {"firstresult": True},
    "hooks/afterRequest": {"firstresult": False},
}


class ServerSupportPlugin:
    async def initialize(self, **kwargs: Any) -> None:
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext) -> None:
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs: Any) -> None:
        """No-op — no resources to release."""
        pass
