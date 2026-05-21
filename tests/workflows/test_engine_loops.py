import pytest
from pydantic import BaseModel

from machine_core.plugins.workflow_support.step import step, StepContext
from machine_core.plugins.workflow_support.workflow import Workflow
from machine_core.plugins.workflow_support.run import RunStatus
from machine_core.plugins.workflow_support.engine import DefaultExecutionEngine


class Counter(BaseModel):
    value: int


@step(name="increment", input_schema=Counter, output_schema=Counter)
async def increment(ctx: StepContext) -> Counter:
    return Counter(value=ctx.input_data.value + 1)


class TestDoWhile:
    @pytest.mark.asyncio
    async def test_dowhile_executes_body_then_checks(self):
        call_count = 0

        @step(name="count_up", input_schema=Counter, output_schema=Counter)
        async def count_up(ctx: StepContext) -> Counter:
            nonlocal call_count
            call_count += 1
            return Counter(value=ctx.input_data.value + 1)

        def still_under_three(state: dict) -> bool:
            return state.get("last_value", 0) < 3

        wf = Workflow(name="dw")
        wf.dowhile(still_under_three, count_up)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=Counter(value=0))
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_dowhile_runs_at_least_once(self):
        call_count = 0

        @step(name="once", input_schema=Counter, output_schema=Counter)
        async def once(ctx: StepContext) -> Counter:
            nonlocal call_count
            call_count += 1
            return Counter(value=ctx.input_data.value + 1)

        def always_false(state: dict) -> bool:
            return False

        wf = Workflow(name="dw-once")
        wf.dowhile(always_false, once)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=Counter(value=10))
        assert run.status == RunStatus.COMPLETED
        assert call_count == 1


class TestDoUntil:
    @pytest.mark.asyncio
    async def test_dountil_repeats_until_condition_true(self):
        call_count = 0

        @step(name="inc", input_schema=Counter, output_schema=Counter)
        async def inc(ctx: StepContext) -> Counter:
            nonlocal call_count
            call_count += 1
            return Counter(value=ctx.input_data.value + 1)

        def reached_five(state: dict) -> bool:
            return state.get("last_value", 0) >= 5

        wf = Workflow(name="du")
        wf.dountil(reached_five, inc)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=Counter(value=0))
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 5
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_dountil_runs_at_least_once(self):
        call_count = 0

        @step(name="once", input_schema=Counter, output_schema=Counter)
        async def once(ctx: StepContext) -> Counter:
            nonlocal call_count
            call_count += 1
            return Counter(value=99)

        def always_true(state: dict) -> bool:
            return True

        wf = Workflow(name="du-once")
        wf.dountil(always_true, once)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=Counter(value=0))
        assert run.status == RunStatus.COMPLETED
        assert call_count == 1
