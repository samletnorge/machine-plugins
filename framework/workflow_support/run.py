"""WorkflowRun — tracks the full lifecycle of a single workflow execution."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


class StepResult(BaseModel):
    """Records the outcome of a single step execution."""

    step_name: str
    status: str
    output: Any | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class WorkflowRun(BaseModel):
    """Tracks the full lifecycle of a single workflow execution."""

    model_config = {"arbitrary_types_allowed": True}

    workflow_name: str
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    status: RunStatus = RunStatus.PENDING
    step_results: list[StepResult] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)

    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: Any | None = None
    error: str | None = None

    # Suspend/resume
    suspended_at_node: int | None = None
    suspend_message: str | None = None
    resume_data: Any | None = None

    # Current position
    current_node_index: int = 0

    def start(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, output: Any = None) -> None:
        self.status = RunStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.output = output

    def fail(self, error: str) -> None:
        self.status = RunStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def suspend_at(self, node_index: int, message: str = "") -> None:
        self.status = RunStatus.SUSPENDED
        self.suspended_at_node = node_index
        self.suspend_message = message

    def resume(self, resume_data: Any = None) -> None:
        self.status = RunStatus.RUNNING
        self.resume_data = resume_data

    def record_step(self, result: StepResult) -> None:
        self.step_results.append(result)

    def state_at_step(self, index: int) -> list[StepResult]:
        """Time-travel: return step results up to and including the given index."""
        return self.step_results[: index + 1]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
