"""Temporal-style durable workflow execution adapter."""

from __future__ import annotations

from typing import Any

from workflow_support.adapters.base import ExternalEngineAdapter
from workflow_support.workflow import Workflow, NodeType


class TemporalAdapter(ExternalEngineAdapter):
    """Adapter for Temporal-style durable workflow execution.

    Maps machine-core workflow steps to Temporal activities and workflows.
    Requires the Temporal SDK for actual execution.
    """

    def __init__(
        self, endpoint: str = "localhost:7233", namespace: str = "default"
    ) -> None:
        self.endpoint = endpoint
        self.namespace = namespace
        self.registered_workflows: dict[str, Workflow] = {}

    def register_workflow(self, workflow: Workflow) -> None:
        self.registered_workflows[workflow.name] = workflow

    def build_function_config(self, workflow_name: str) -> dict[str, Any]:
        if workflow_name not in self.registered_workflows:
            raise KeyError(f"Workflow '{workflow_name}' not registered")

        wf = self.registered_workflows[workflow_name]
        activities = []
        for i, node in enumerate(wf.nodes):
            activity: dict[str, Any] = {
                "index": i,
                "type": node.node_type.value,
            }
            if node.step:
                activity["activity_type"] = node.step.name
            if node.steps:
                activity["parallel_activities"] = [s.name for s in node.steps]
            activities.append(activity)

        return {
            "workflow_type": workflow_name,
            "namespace": self.namespace,
            "task_queue": f"machine-core-{workflow_name}",
            "activities": activities,
        }

    async def trigger(self, workflow_name: str, data: dict[str, Any]) -> dict[str, Any]:
        if workflow_name not in self.registered_workflows:
            raise KeyError(f"Workflow '{workflow_name}' not registered")

        return await self._start_workflow_execution(workflow_name, data)

    async def _start_workflow_execution(
        self, workflow_name: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Start a workflow execution via Temporal. Override in tests or use Temporal SDK."""
        raise NotImplementedError(
            "Temporal SDK integration required. Install temporalio and configure client."
        )
