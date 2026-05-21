import pytest
from pydantic import BaseModel

from machine_core.plugins.workflow_support.step import (
    step,
    Step,
    StepContext,
    StepStatus,
)


class AddInput(BaseModel):
    a: int
    b: int


class AddOutput(BaseModel):
    result: int


class TestStepDecorator:
    def test_creates_step_from_function(self):
        @step(name="add", input_schema=AddInput, output_schema=AddOutput)
        async def add(ctx: StepContext) -> AddOutput:
            data = ctx.input_data
            return AddOutput(result=data.a + data.b)

        assert isinstance(add, Step)
        assert add.name == "add"
        assert add.input_schema is AddInput
        assert add.output_schema is AddOutput

    def test_step_name_defaults_to_function_name(self):
        @step(input_schema=AddInput, output_schema=AddOutput)
        async def my_adder(ctx: StepContext) -> AddOutput:
            return AddOutput(result=0)

        assert my_adder.name == "my_adder"

    @pytest.mark.asyncio
    async def test_step_execute_validates_input(self):
        @step(name="add", input_schema=AddInput, output_schema=AddOutput)
        async def add(ctx: StepContext) -> AddOutput:
            return AddOutput(result=ctx.input_data.a + ctx.input_data.b)

        ctx = StepContext(input_data=AddInput(a=2, b=3), state={}, previous_output=None)
        result = await add.execute(ctx)
        assert result.result == 5

    @pytest.mark.asyncio
    async def test_step_execute_validates_output_type(self):
        @step(name="bad", input_schema=AddInput, output_schema=AddOutput)
        async def bad(ctx: StepContext) -> AddOutput:
            return {"wrong": "type"}  # type: ignore

        ctx = StepContext(input_data=AddInput(a=1, b=1), state={}, previous_output=None)
        with pytest.raises(TypeError, match="output.*AddOutput"):
            await bad.execute(ctx)

    @pytest.mark.asyncio
    async def test_step_execute_invalid_input_raises(self):
        @step(name="add", input_schema=AddInput, output_schema=AddOutput)
        async def add(ctx: StepContext) -> AddOutput:
            return AddOutput(result=ctx.input_data.a + ctx.input_data.b)

        ctx = StepContext(input_data={"a": "not_int"}, state={}, previous_output=None)
        with pytest.raises(Exception):
            await add.execute(ctx)


class TestStepContext:
    def test_context_holds_state(self):
        ctx = StepContext(
            input_data=AddInput(a=1, b=2),
            state={"counter": 5},
            previous_output=None,
        )
        assert ctx.state["counter"] == 5

    def test_context_holds_previous_output(self):
        prev = AddOutput(result=10)
        ctx = StepContext(
            input_data=AddInput(a=1, b=2),
            state={},
            previous_output=prev,
        )
        assert ctx.previous_output.result == 10


class TestStepStatus:
    def test_status_values(self):
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"
