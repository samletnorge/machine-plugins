import pytest
from pydantic import BaseModel

from workflow_support.step import step, StepContext
from workflow_support.workflow import Workflow
from workflow_support.run import RunStatus
from workflow_support.engine import DefaultExecutionEngine


class Val(BaseModel):
    value: int


@step(name="double", input_schema=Val, output_schema=Val)
async def double(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value * 2)


@step(name="add_one", input_schema=Val, output_schema=Val)
async def add_one(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value + 1)


class TestSuspendResume:
    @pytest.mark.asyncio
    async def test_suspend_pauses_workflow(self):
        wf = Workflow(name="sus")
        wf.then(double).suspend("Need human approval").then(add_one)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=Val(value=5))
        assert run.status == RunStatus.SUSPENDED
        assert run.suspended_at_node == 1
        assert run.suspend_message == "Need human approval"
        assert len(run.step_results) == 1

    @pytest.mark.asyncio
    async def test_resume_continues_from_suspend(self):
        wf = Workflow(name="sus")
        wf.then(double).suspend("Need approval").then(add_one)
        engine = DefaultExecutionEngine()

        run = await engine.execute(wf, input_data=Val(value=5))
        assert run.status == RunStatus.SUSPENDED

        run.resume(resume_data={"approved": True})
        run.current_node_index = run.suspended_at_node + 1
        last_output = Val(**run.step_results[-1].output)
        run = await engine.execute(wf, input_data=last_output, run=run)
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 11
