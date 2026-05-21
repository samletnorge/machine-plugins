"""Abstract interface for external workflow execution engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from machine_core.plugins.workflow_support.workflow import Workflow


class ExternalEngineAdapter(ABC):
    """Abstract interface for external workflow execution engines.

    External adapters are separate plugins that depend on workflow-support.
    They register via machine.register("workflow-adapter", "inngest", self).
    """

    @abstractmethod
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow with the external engine."""
        ...

    @abstractmethod
    async def trigger(self, workflow_name: str, data: dict[str, Any]) -> dict[str, Any]:
        """Trigger a workflow execution."""
        ...

    @abstractmethod
    def build_function_config(self, workflow_name: str) -> dict[str, Any]:
        """Build the engine-specific configuration for a workflow."""
        ...
