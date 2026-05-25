import pytest
from pydantic import BaseModel

from workflow_support.step import step, StepContext
from workflow_support.workflow import Workflow
from workflow_support.run import RunStatus
from workflow_support.engine import DefaultExecutionEngine


class ItemsList(BaseModel):
    items: list[int]


class SingleItem(BaseModel):
    value: int


class ProcessedItem(BaseModel):
    value: int


@step(name="produce_items", input_schema=SingleItem, output_schema=ItemsList)
async def produce_items(ctx: StepContext) -> ItemsList:
    return ItemsList(items=[1, 2, 3, 4, 5])


@step(name="square_item", input_schema=SingleItem, output_schema=ProcessedItem)
async def square_item(ctx: StepContext) -> ProcessedItem:
    return ProcessedItem(value=ctx.input_data.value**2)


class TestForeach:
    @pytest.mark.asyncio
    async def test_foreach_iterates_over_items(self):
        wf = Workflow(name="fe")
        wf.foreach(produce_items, square_item)
        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=SingleItem(value=0))
        assert run.status == RunStatus.COMPLETED
        assert len(run.step_results) == 6
        assert len(run.output) == 5
        values = [r.value for r in run.output]
        assert values == [1, 4, 9, 16, 25]
