"""memory-support: Defines the 'memory' category with thread-based conversation memory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

HOOKSPECS: dict[str, dict[str, Any]] = {
    "hooks/beforeMemoryStore": {"firstresult": False},
    "hooks/afterMemoryStore": {"firstresult": False},
    "hooks/beforeFactExtraction": {"firstresult": False},
    "hooks/afterFactExtraction": {"firstresult": False},
}


class MemorySupportPlugin:
    async def initialize(self, **kwargs: Any) -> None:
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext) -> None:
        ctx.register_category(
            "memory",
            operations={
                "create_thread": {"method": "POST", "on": "item", "path": "threads"},
                "list_threads": {"method": "GET", "on": "item", "path": "threads"},
                "get_thread": {
                    "method": "GET",
                    "on": "item",
                    "path": "threads/{thread_id}",
                },
                "add_message": {
                    "method": "POST",
                    "on": "item",
                    "path": "threads/{thread_id}/messages",
                },
                "delete_thread": {
                    "method": "DELETE",
                    "on": "item",
                    "path": "threads/{thread_id}",
                },
            },
        )
        ctx.register_category("storage-backend")
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs: Any) -> None:
        """No-op — no resources to release."""
        pass
