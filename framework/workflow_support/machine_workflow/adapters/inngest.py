"""Inngest-style HTTP webhook-triggered workflow adapter."""

from __future__ import annotations

from typing import Any

from workflow_support.adapters.base import ExternalEngineAdapter
from workflow_support.workflow import Workflow, NodeType


class InngestAdapter(ExternalEngineAdapter):
    """Adapter for Inngest-style HTTP webhook-triggered workflow execution.

    Translates machine-core workflows into Inngest function definitions
    and triggers execution via HTTP events.
    """

    def __init__(self, base_url: str = "http://localhost:8288") -> None:
        self.base_url = base_url.rstrip("/")
        self.registered_workflows: dict[str, Workflow] = {}

    def register_workflow(self, workflow: Workflow) -> None:
        self.registered_workflows[workflow.name] = workflow

    def build_function_config(self, workflow_name: str) -> dict[str, Any]:
        if workflow_name not in self.registered_workflows:
            raise KeyError(f"Workflow '{workflow_name}' not registered")

        wf = self.registered_workflows[workflow_name]
        steps = []
        for i, node in enumerate(wf.nodes):
            step_config: dict[str, Any] = {
                "index": i,
                "type": node.node_type.value,
            }
            if node.step:
                step_config["name"] = node.step.name
            if node.steps:
                step_config["parallel_steps"] = [s.name for s in node.steps]
            steps.append(step_config)

        return {
            "id": workflow_name,
            "name": workflow_name,
            "triggers": [{"event": f"workflow/{workflow_name}"}],
            "steps": steps,
        }

    async def trigger(self, workflow_name: str, data: dict[str, Any]) -> dict[str, Any]:
        if workflow_name not in self.registered_workflows:
            raise KeyError(f"Workflow '{workflow_name}' not registered")

        event = {
            "name": f"workflow/{workflow_name}",
            "data": data,
        }
        return await self._send_event(event)

    async def _send_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Send an event to the Inngest API. Override in tests."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/e/key",
                json=[event],
            )
            response.raise_for_status()
            return response.json()
