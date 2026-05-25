import asyncio
import pytest
from pydantic import BaseModel

from workflow_support.step import step, StepContext
from workflow_support.workflow import Workflow
from workflow_support.run import WorkflowRun, RunStatus
from workflow_support.engine import DefaultExecutionEngine


class NumIn(BaseModel):
    value: int


class NumOut(BaseModel):
    value: int


class ListIn(BaseModel):
    items: list[int]


class ListOut(BaseModel):
    items: list[int]


@step(name="double", input_schema=NumIn, output_schema=NumOut)
async def double(ctx: StepContext) -> NumOut:
    return NumOut(value=ctx.input_data.value * 2)


@step(name="add_ten", input_schema=NumIn, output_schema=NumOut)
async def add_ten(ctx: StepContext) -> NumOut:
    return NumOut(value=ctx.input_data.value + 10)


@step(name="negate", input_schema=NumIn, output_schema=NumOut)
async def negate(ctx: StepContext) -> NumOut:
    return NumOut(value=-ctx.input_data.value)


@step(name="fail_step", input_schema=NumIn, output_schema=NumOut)
async def fail_step(ctx: StepContext) -> NumOut:
    raise ValueError("intentional failure")


class TestDefaultEngineSequential:
    @pytest.mark.asyncio
    async def test_single_step(self):
        wf = Workflow(name="single")
        wf.then(double)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=5))
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 10

    @pytest.mark.asyncio
    async def test_chained_steps(self):
        wf = Workflow(name="chain")
        wf.then(double).then(add_ten)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=3))
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 16

    @pytest.mark.asyncio
    async def test_step_results_recorded(self):
        wf = Workflow(name="recorded")
        wf.then(double).then(add_ten)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=1))
        assert len(run.step_results) == 2
        assert run.step_results[0].step_name == "double"
        assert run.step_results[1].step_name == "add_ten"

    @pytest.mark.asyncio
    async def test_failed_step_marks_run_failed(self):
        wf = Workflow(name="fail")
        wf.then(fail_step)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=1))
        assert run.status == RunStatus.FAILED
        assert "intentional failure" in run.error


class TestDefaultEngineParallel:
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        wf = Workflow(name="par")
        wf.parallel([double, add_ten])
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=5))
        assert run.status == RunStatus.COMPLETED
        assert run.output["double"].value == 10
        assert run.output["add_ten"].value == 15

    @pytest.mark.asyncio
    async def test_parallel_then_sequential(self):
        wf = Workflow(name="par-seq")
        wf.then(double).parallel([add_ten, negate]).then(double)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=3))
        assert run.status == RunStatus.COMPLETED
        assert len(run.step_results) == 4


class TestDefaultEngineBranch:
    @pytest.mark.asyncio
    async def test_branch_true(self):
        def is_positive(state: dict) -> bool:
            return state.get("last_value", 0) > 0

        wf = Workflow(name="br")
        wf.branch(is_positive, {True: double, False: negate})
        engine = DefaultExecutionEngine()
        run = await engine.execute(
            wf, input_data=NumIn(value=5), initial_state={"last_value": 5}
        )
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 10

    @pytest.mark.asyncio
    async def test_branch_false(self):
        def is_positive(state: dict) -> bool:
            return state.get("last_value", 0) > 0

        wf = Workflow(name="br")
        wf.branch(is_positive, {True: double, False: negate})
        engine = DefaultExecutionEngine()
        run = await engine.execute(
            wf, input_data=NumIn(value=5), initial_state={"last_value": -1}
        )
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == -5


class TestDefaultEngineSleep:
    @pytest.mark.asyncio
    async def test_sleep_node(self):
        wf = Workflow(name="sl")
        wf.then(double).sleep(0.01).then(add_ten)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=NumIn(value=2))
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 14
