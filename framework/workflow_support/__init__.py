"""workflow-support: Defines the 'workflow' and 'execution-engine' categories with lifecycle hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

HOOKSPECS: dict[str, dict[str, Any]] = {
    "hooks/collectWorkflows": {"firstresult": False},
    "hooks/beforeWorkflowRun": {"firstresult": True},
    "hooks/afterWorkflowRun": {"firstresult": True},
}


class WorkflowSupportPlugin:
    async def initialize(self, **kwargs: Any) -> None:
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext) -> None:
        ctx.register_category(
            "workflow",
            operations={
                "start": {"method": "POST", "on": "item"},
                "runs": {"method": "GET", "on": "item"},
                "get_run": {"method": "GET", "on": "item", "path": "runs/{run_id}"},
                "resume": {
                    "method": "POST",
                    "on": "item",
                    "path": "runs/{run_id}/resume",
                },
            },
        )
        ctx.register_category("execution-engine")
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs: Any) -> None:
        """No-op — no resources to release."""
        pass
