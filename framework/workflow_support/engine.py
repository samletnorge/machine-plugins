"""Workflow execution engines."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from machine_core.plugins.workflow_support.run import RunStatus, StepResult, WorkflowRun
from machine_core.plugins.workflow_support.step import StepContext
from machine_core.plugins.workflow_support.workflow import (
    NodeType,
    Workflow,
    WorkflowNode,
)


class ExecutionEngine(ABC):
    """Abstract base for workflow execution engines."""

    @abstractmethod
    async def execute(
        self,
        workflow: Workflow,
        input_data: BaseModel,
        initial_state: dict[str, Any] | None = None,
        run: WorkflowRun | None = None,
    ) -> WorkflowRun: ...


class DefaultExecutionEngine(ExecutionEngine):
    """Synchronous step-by-step execution engine.

    Walks the workflow node list in order. Parallel nodes use asyncio.gather.
    """

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

        current_input = input_data
        previous_output: Any = None

        start_index = run.current_node_index
        for i in range(start_index, len(workflow.nodes)):
            node = workflow.nodes[i]
            run.current_node_index = i

            try:
                result = await self._execute_node(
                    node, current_input, state, previous_output, run
                )
                if result is not None:
                    previous_output = result
                    if isinstance(result, BaseModel):
                        current_input = result
                    if isinstance(result, BaseModel) and hasattr(result, "value"):
                        state["last_value"] = result.value
            except _SuspendSignal as sig:
                run.suspend_at(node_index=i, message=sig.message)
                return run
            except Exception as e:
                run.fail(error=str(e))
                return run

        run.complete(output=previous_output)
        return run

    async def _execute_node(
        self,
        node: WorkflowNode,
        current_input: Any,
        state: dict[str, Any],
        previous_output: Any,
        run: WorkflowRun,
    ) -> Any:
        if node.node_type == NodeType.SEQUENTIAL:
            return await self._run_step(
                node.step, current_input, state, previous_output, run
            )

        elif node.node_type == NodeType.PARALLEL:
            return await self._run_parallel(
                node.steps, current_input, state, previous_output, run
            )

        elif node.node_type == NodeType.BRANCH:
            branch_key = node.condition(state)
            selected_step = node.branches.get(branch_key)
            if selected_step is None:
                return previous_output
            return await self._run_step(
                selected_step, current_input, state, previous_output, run
            )

        elif node.node_type == NodeType.FOREACH:
            return await self._run_foreach(
                node, current_input, state, previous_output, run
            )

        elif node.node_type == NodeType.DOWHILE:
            return await self._run_dowhile(
                node, current_input, state, previous_output, run
            )

        elif node.node_type == NodeType.DOUNTIL:
            return await self._run_dountil(
                node, current_input, state, previous_output, run
            )

        elif node.node_type == NodeType.SLEEP:
            await asyncio.sleep(node.duration)
            return previous_output

        elif node.node_type == NodeType.SUSPEND:
            raise _SuspendSignal(node.message)

        else:
            raise ValueError(f"Unknown node type: {node.node_type}")

    async def _run_step(
        self, step, current_input, state, previous_output, run: WorkflowRun
    ) -> BaseModel:
        started = datetime.now(timezone.utc)
        ctx = StepContext(
            input_data=current_input,
            state=state,
            previous_output=previous_output,
        )
        try:
            output = await step.execute(ctx)
            completed = datetime.now(timezone.utc)
            run.record_step(
                StepResult(
                    step_name=step.name,
                    status="completed",
                    output=output.model_dump()
                    if isinstance(output, BaseModel)
                    else output,
                    started_at=started,
                    completed_at=completed,
                )
            )
            return output
        except Exception:
            completed = datetime.now(timezone.utc)
            import traceback

            run.record_step(
                StepResult(
                    step_name=step.name,
                    status="failed",
                    error=traceback.format_exc(),
                    started_at=started,
                    completed_at=completed,
                )
            )
            raise

    async def _run_parallel(
        self, steps, current_input, state, previous_output, run: WorkflowRun
    ) -> dict[str, BaseModel]:
        async def _run_one(s):
            return s.name, await self._run_step(
                s, current_input, state, previous_output, run
            )

        results = await asyncio.gather(*[_run_one(s) for s in steps])
        return {name: output for name, output in results}

    async def _run_foreach(
        self,
        node: WorkflowNode,
        current_input,
        state,
        previous_output,
        run: WorkflowRun,
    ) -> list[BaseModel]:
        items_output = await self._run_step(
            node.items_step, current_input, state, previous_output, run
        )
        items = getattr(items_output, "items", [])
        results = []
        for item in items:
            item_input = (
                type(current_input)(value=item)
                if hasattr(current_input, "value")
                else current_input
            )
            out = await self._run_step(
                node.body_step, item_input, state, items_output, run
            )
            results.append(out)
        return results

    async def _run_dowhile(
        self,
        node: WorkflowNode,
        current_input,
        state,
        previous_output,
        run: WorkflowRun,
    ) -> Any:
        result = previous_output
        while True:
            result = await self._run_step(
                node.loop_body, current_input, state, result, run
            )
            if isinstance(result, BaseModel) and hasattr(result, "value"):
                state["last_value"] = result.value
                current_input = result
            if not node.loop_condition(state):
                break
        return result

    async def _run_dountil(
        self,
        node: WorkflowNode,
        current_input,
        state,
        previous_output,
        run: WorkflowRun,
    ) -> Any:
        result = previous_output
        while True:
            result = await self._run_step(
                node.loop_body, current_input, state, result, run
            )
            if isinstance(result, BaseModel) and hasattr(result, "value"):
                state["last_value"] = result.value
                current_input = result
            if node.loop_condition(state):
                break
        return result


class _SuspendSignal(Exception):
    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)
