"""Workflow-as-step — nest a workflow inside another workflow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from workflow_support.engine import DefaultExecutionEngine
from workflow_support.step import Step, StepContext
from workflow_support.workflow import Workflow


def workflow_as_step(
    workflow: Workflow,
    input_schema: type[BaseModel],
    output_schema: type[BaseModel],
    name: str | None = None,
    engine: DefaultExecutionEngine | None = None,
) -> Step:
    """Wrap a Workflow as a Step so it can be nested inside another workflow."""
    step_name = name or workflow.name
    _engine = engine or DefaultExecutionEngine()

    async def _run_workflow(ctx: StepContext) -> BaseModel:
        run = await _engine.execute(workflow, input_data=ctx.input_data)
        if run.output is None:
            raise RuntimeError(f"Nested workflow '{workflow.name}' produced no output")
        return run.output

    return Step(
        fn=_run_workflow,
        name=step_name,
        input_schema=input_schema,
        output_schema=output_schema,
    )
