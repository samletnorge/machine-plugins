"""Workflow DAG builder with fluent API."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable

from machine_core.plugins.workflow_support.step import Step


class NodeType(str, enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BRANCH = "branch"
    FOREACH = "foreach"
    DOWHILE = "dowhile"
    DOUNTIL = "dountil"
    SLEEP = "sleep"
    SUSPEND = "suspend"


@dataclass
class WorkflowNode:
    """A single node in the workflow DAG."""

    node_type: NodeType

    # SEQUENTIAL
    step: Step | None = None

    # PARALLEL
    steps: list[Step] = field(default_factory=list)

    # BRANCH
    condition: Callable[[dict], Any] | None = None
    branches: dict[Any, Step] = field(default_factory=dict)

    # FOREACH
    items_step: Step | None = None
    body_step: Step | None = None

    # DOWHILE / DOUNTIL
    loop_condition: Callable[[dict], bool] | None = None
    loop_body: Step | None = None

    # SLEEP
    duration: float = 0.0

    # SUSPEND
    message: str = ""


class Workflow:
    """A step-based DAG workflow with a fluent builder API."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.nodes: list[WorkflowNode] = []

    def then(self, s: Step) -> Workflow:
        """Add a sequential step."""
        self.nodes.append(WorkflowNode(node_type=NodeType.SEQUENTIAL, step=s))
        return self

    def parallel(self, steps: list[Step]) -> Workflow:
        """Add a set of steps that execute concurrently."""
        self.nodes.append(WorkflowNode(node_type=NodeType.PARALLEL, steps=steps))
        return self

    def branch(
        self, condition: Callable[[dict], Any], branches: dict[Any, Step]
    ) -> Workflow:
        """Add a conditional branch node."""
        self.nodes.append(
            WorkflowNode(
                node_type=NodeType.BRANCH, condition=condition, branches=branches
            )
        )
        return self

    def foreach(self, items_step: Step, body_step: Step) -> Workflow:
        """Add a foreach loop: items_step produces a list, body_step runs for each."""
        self.nodes.append(
            WorkflowNode(
                node_type=NodeType.FOREACH, items_step=items_step, body_step=body_step
            )
        )
        return self

    def dowhile(self, condition: Callable[[dict], bool], body: Step) -> Workflow:
        """Add a do-while loop: executes body, then checks condition. Repeats while True."""
        self.nodes.append(
            WorkflowNode(
                node_type=NodeType.DOWHILE, loop_condition=condition, loop_body=body
            )
        )
        return self

    def dountil(self, condition: Callable[[dict], bool], body: Step) -> Workflow:
        """Add a do-until loop: executes body, then checks condition. Repeats until True."""
        self.nodes.append(
            WorkflowNode(
                node_type=NodeType.DOUNTIL, loop_condition=condition, loop_body=body
            )
        )
        return self

    def sleep(self, duration: float) -> Workflow:
        """Add a sleep/wait node."""
        self.nodes.append(WorkflowNode(node_type=NodeType.SLEEP, duration=duration))
        return self

    def suspend(self, message: str = "") -> Workflow:
        """Add a suspend node — pauses execution for human input."""
        self.nodes.append(WorkflowNode(node_type=NodeType.SUSPEND, message=message))
        return self

    def __repr__(self) -> str:
        return f"Workflow(name={self.name!r}, nodes={len(self.nodes)})"
