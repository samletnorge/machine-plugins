"""EventedExecutionEngine — pubsub-driven workflow execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel

from machine_core.plugins.workflow_support.engine import (
    DefaultExecutionEngine,
    ExecutionEngine,
    _SuspendSignal,
)
from machine_core.plugins.workflow_support.run import RunStatus, StepResult, WorkflowRun
from machine_core.plugins.workflow_support.step import StepContext
from machine_core.plugins.workflow_support.workflow import (
    NodeType,
    Workflow,
    WorkflowNode,
)


@dataclass
class WorkflowEvent:
    """An event emitted during workflow execution."""

    event_type: str
    workflow_name: str
    run_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    step_name: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


class EventedExecutionEngine(ExecutionEngine):
    """Pubsub-driven execution engine that wraps DefaultExecutionEngine
    and emits events at workflow/step lifecycle boundaries."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[WorkflowEvent], Any]] = []
        self._inner = DefaultExecutionEngine()

    def on_event(self, listener: Callable[[WorkflowEvent], Any]) -> None:
        """Register an event listener."""
        self._listeners.append(listener)

    def _emit(self, event: WorkflowEvent) -> None:
        for listener in self._listeners:
            listener(event)

    async def execute(
        self,
        workflow: Workflow,
        input_data: BaseModel,
        initial_state: dict[str, Any] | None = None,
        run: WorkflowRun | None = None,
    ) -> WorkflowRun:
        if run is None:
            run = WorkflowRun(workflow_name=workflow.name)

        state = initial_state or {}
        run.start()
        self._emit(
            WorkflowEvent(
                event_type="workflow_started",
                workflow_name=workflow.name,
                run_id=run.run_id,
            )
        )

        current_input = input_data
        previous_output: Any = None

        for i in range(run.current_node_index, len(workflow.nodes)):
            node = workflow.nodes[i]
            run.current_node_index = i

            try:
                result = await self._execute_node_with_events(
                    node, current_input, state, previous_output, run, workflow.name
                )
                if result is not None:
                    previous_output = result
                    if isinstance(result, BaseModel):
                        current_input = result
                    if isinstance(result, BaseModel) and hasattr(result, "value"):
                        state["last_value"] = result.value
            except _SuspendSignal as sig:
                run.suspend_at(node_index=i, message=sig.message)
                self._emit(
                    WorkflowEvent(
                        event_type="workflow_suspended",
                        workflow_name=workflow.name,
                        run_id=run.run_id,
                        data={"message": sig.message},
                    )
                )
                return run
            except Exception as e:
                run.fail(error=str(e))
                self._emit(
                    WorkflowEvent(
                        event_type="workflow_failed",
                        workflow_name=workflow.name,
                        run_id=run.run_id,
                        data={"error": str(e)},
                    )
                )
                return run

        run.complete(output=previous_output)
        self._emit(
            WorkflowEvent(
                event_type="workflow_completed",
                workflow_name=workflow.name,
                run_id=run.run_id,
            )
        )
        return run

    async def _execute_node_with_events(
        self,
        node: WorkflowNode,
        current_input: Any,
        state: dict[str, Any],
        previous_output: Any,
        run: WorkflowRun,
        workflow_name: str,
    ) -> Any:
        if node.node_type == NodeType.SEQUENTIAL:
            return await self._run_step_with_events(
                node.step, current_input, state, previous_output, run, workflow_name
            )
        elif node.node_type == NodeType.PARALLEL:
            return await self._run_parallel_with_events(
                node.steps, current_input, state, previous_output, run, workflow_name
            )
        elif node.node_type == NodeType.BRANCH:
            branch_key = node.condition(state)
            selected = node.branches.get(branch_key)
            if selected is None:
                return previous_output
            return await self._run_step_with_events(
                selected, current_input, state, previous_output, run, workflow_name
            )
        elif node.node_type == NodeType.SLEEP:
            await asyncio.sleep(node.duration)
            return previous_output
        elif node.node_type == NodeType.SUSPEND:
            raise _SuspendSignal(node.message)
        elif node.node_type == NodeType.DOWHILE:
            result = previous_output
            while True:
                result = await self._run_step_with_events(
                    node.loop_body, current_input, state, result, run, workflow_name
                )
                if isinstance(result, BaseModel) and hasattr(result, "value"):
                    state["last_value"] = result.value
                    current_input = result
                if not node.loop_condition(state):
                    break
            return result
        elif node.node_type == NodeType.DOUNTIL:
            result = previous_output
            while True:
                result = await self._run_step_with_events(
                    node.loop_body, current_input, state, result, run, workflow_name
                )
                if isinstance(result, BaseModel) and hasattr(result, "value"):
                    state["last_value"] = result.value
                    current_input = result
                if node.loop_condition(state):
                    break
            return result
        elif node.node_type == NodeType.FOREACH:
            items_output = await self._run_step_with_events(
                node.items_step,
                current_input,
                state,
                previous_output,
                run,
                workflow_name,
            )
            items = getattr(items_output, "items", [])
            results = []
            for item in items:
                item_input = (
                    type(current_input)(value=item)
                    if hasattr(current_input, "value")
                    else current_input
                )
                out = await self._run_step_with_events(
                    node.body_step, item_input, state, items_output, run, workflow_name
                )
                results.append(out)
            return results
        else:
            raise ValueError(f"Unknown node type: {node.node_type}")

    async def _run_step_with_events(
        self,
        s: Any,
        current_input: Any,
        state: dict[str, Any],
        previous_output: Any,
        run: WorkflowRun,
        workflow_name: str,
    ) -> BaseModel:
        self._emit(
            WorkflowEvent(
                event_type="step_started",
                workflow_name=workflow_name,
                run_id=run.run_id,
                step_name=s.name,
            )
        )
        started = datetime.now(timezone.utc)
        ctx = StepContext(
            input_data=current_input, state=state, previous_output=previous_output
        )
        try:
            output = await s.execute(ctx)
            completed = datetime.now(timezone.utc)
            run.record_step(
                StepResult(
                    step_name=s.name,
                    status="completed",
                    output=output.model_dump()
                    if isinstance(output, BaseModel)
                    else output,
                    started_at=started,
                    completed_at=completed,
                )
            )
            self._emit(
                WorkflowEvent(
                    event_type="step_completed",
                    workflow_name=workflow_name,
                    run_id=run.run_id,
                    step_name=s.name,
                )
            )
            return output
        except Exception as e:
            completed = datetime.now(timezone.utc)
            run.record_step(
                StepResult(
                    step_name=s.name,
                    status="failed",
                    error=str(e),
                    started_at=started,
                    completed_at=completed,
                )
            )
            self._emit(
                WorkflowEvent(
                    event_type="step_failed",
                    workflow_name=workflow_name,
                    run_id=run.run_id,
                    step_name=s.name,
                    data={"error": str(e)},
                )
            )
            raise

    async def _run_parallel_with_events(
        self,
        steps: list[Any],
        current_input: Any,
        state: dict[str, Any],
        previous_output: Any,
        run: WorkflowRun,
        workflow_name: str,
    ) -> dict[str, BaseModel]:
        async def _one(s: Any) -> tuple[str, BaseModel]:
            return s.name, await self._run_step_with_events(
                s, current_input, state, previous_output, run, workflow_name
            )

        results = await asyncio.gather(*[_one(s) for s in steps])
        return {name: output for name, output in results}
