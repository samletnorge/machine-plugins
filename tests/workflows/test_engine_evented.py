"""Task 8: EventedExecutionEngine — pubsub-driven engine tests."""

import pytest
from pydantic import BaseModel

from workflow_support.step import step, StepContext
from workflow_support.workflow import Workflow
from workflow_support.run import RunStatus
from workflow_support.events import (
    EventedExecutionEngine,
    WorkflowEvent,
)


class Val(BaseModel):
    value: int


@step(name="double", input_schema=Val, output_schema=Val)
async def double(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value * 2)


@step(name="add_ten", input_schema=Val, output_schema=Val)
async def add_ten(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value + 10)


class TestEventedEngine:
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        wf = Workflow(name="evented")
        wf.then(double).then(add_ten)
        engine = EventedExecutionEngine()
        run = await engine.execute(wf, input_data=Val(value=3))
        assert run.status == RunStatus.COMPLETED
        assert run.output.value == 16  # 3*2=6, 6+10=16

    @pytest.mark.asyncio
    async def test_emits_events(self):
        events: list[WorkflowEvent] = []

        wf = Workflow(name="evented")
        wf.then(double).then(add_ten)
        engine = EventedExecutionEngine()
        engine.on_event(lambda e: events.append(e))
        run = await engine.execute(wf, input_data=Val(value=1))
        assert run.status == RunStatus.COMPLETED

        event_types = [e.event_type for e in events]
        assert "workflow_started" in event_types
        assert "workflow_completed" in event_types
        assert event_types.count("step_started") == 2
        assert event_types.count("step_completed") == 2

    @pytest.mark.asyncio
    async def test_emits_step_failed_event(self):
        events: list[WorkflowEvent] = []

        @step(name="boom", input_schema=Val, output_schema=Val)
        async def boom(ctx: StepContext) -> Val:
            raise RuntimeError("kaboom")

        wf = Workflow(name="fail-ev")
        wf.then(boom)
        engine = EventedExecutionEngine()
        engine.on_event(lambda e: events.append(e))
        run = await engine.execute(wf, input_data=Val(value=1))
        assert run.status == RunStatus.FAILED

        event_types = [e.event_type for e in events]
        assert "step_failed" in event_types
        assert "workflow_failed" in event_types

    @pytest.mark.asyncio
    async def test_parallel_emits_events(self):
        events: list[WorkflowEvent] = []

        wf = Workflow(name="par-ev")
        wf.parallel([double, add_ten])
        engine = EventedExecutionEngine()
        engine.on_event(lambda e: events.append(e))
        run = await engine.execute(wf, input_data=Val(value=2))
        assert run.status == RunStatus.COMPLETED
        step_started = [e for e in events if e.event_type == "step_started"]
        assert len(step_started) == 2
