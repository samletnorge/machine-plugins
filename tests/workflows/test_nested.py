"""Task 11: Workflow-as-step (nested workflows) tests."""

import pytest
from pydantic import BaseModel

from machine_core.plugins.workflow_support.step import step, StepContext, Step
from machine_core.plugins.workflow_support.workflow import Workflow
from machine_core.plugins.workflow_support.engine import DefaultExecutionEngine
from machine_core.plugins.workflow_support.nested import workflow_as_step
from machine_core.plugins.workflow_support.run import RunStatus


class Val(BaseModel):
    value: int


@step(name="double", input_schema=Val, output_schema=Val)
async def double(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value * 2)


@step(name="add_one", input_schema=Val, output_schema=Val)
async def add_one(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value + 1)


class TestNestedWorkflow:
    def test_creates_step_from_workflow(self):
        inner = Workflow(name="inner")
        inner.then(double).then(add_one)
        s = workflow_as_step(inner, input_schema=Val, output_schema=Val)
        assert isinstance(s, Step)
        assert s.name == "inner"

    @pytest.mark.asyncio
    async def test_nested_workflow_executes(self):
        inner = Workflow(name="inner")
        inner.then(double).then(add_one)

        outer = Workflow(name="outer")
        inner_step = workflow_as_step(inner, input_schema=Val, output_schema=Val)
        outer.then(inner_step).then(double)

        engine = DefaultExecutionEngine()
        run = await engine.execute(outer, input_data=Val(value=3))
        # inner: 3*2=6, 6+1=7
        # outer continues: 7*2=14
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 14
