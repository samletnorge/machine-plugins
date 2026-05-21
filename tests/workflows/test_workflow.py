import pytest
from pydantic import BaseModel

from machine_core.plugins.workflow_support.step import step, StepContext
from machine_core.plugins.workflow_support.workflow import Workflow, NodeType


class In(BaseModel):
    value: int


class Out(BaseModel):
    value: int


@step(name="double", input_schema=In, output_schema=Out)
async def double_step(ctx: StepContext) -> Out:
    return Out(value=ctx.input_data.value * 2)


@step(name="add_one", input_schema=In, output_schema=Out)
async def add_one_step(ctx: StepContext) -> Out:
    return Out(value=ctx.input_data.value + 1)


@step(name="negate", input_schema=In, output_schema=Out)
async def negate_step(ctx: StepContext) -> Out:
    return Out(value=-ctx.input_data.value)


class TestWorkflowBuilder:
    def test_create_workflow_with_name(self):
        wf = Workflow(name="test-wf")
        assert wf.name == "test-wf"

    def test_then_adds_sequential_node(self):
        wf = Workflow(name="seq")
        wf.then(double_step)
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.SEQUENTIAL
        assert wf.nodes[0].step is double_step

    def test_then_returns_self_for_chaining(self):
        wf = Workflow(name="chain")
        result = wf.then(double_step).then(add_one_step)
        assert result is wf
        assert len(wf.nodes) == 2

    def test_parallel_adds_parallel_node(self):
        wf = Workflow(name="par")
        wf.parallel([double_step, add_one_step])
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.PARALLEL
        assert len(wf.nodes[0].steps) == 2

    def test_branch_adds_branch_node(self):
        def check(state: dict) -> bool:
            return state.get("flag", False)

        wf = Workflow(name="br")
        wf.branch(check, {True: double_step, False: negate_step})
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.BRANCH

    def test_foreach_adds_foreach_node(self):
        wf = Workflow(name="fe")
        wf.foreach(double_step, add_one_step)
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.FOREACH

    def test_dowhile_adds_dowhile_node(self):
        def cond(state: dict) -> bool:
            return state.get("count", 0) < 3

        wf = Workflow(name="dw")
        wf.dowhile(cond, double_step)
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.DOWHILE

    def test_dountil_adds_dountil_node(self):
        def cond(state: dict) -> bool:
            return state.get("done", False)

        wf = Workflow(name="du")
        wf.dountil(cond, double_step)
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.DOUNTIL

    def test_sleep_adds_sleep_node(self):
        wf = Workflow(name="sl")
        wf.sleep(1.5)
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.SLEEP
        assert wf.nodes[0].duration == 1.5

    def test_suspend_adds_suspend_node(self):
        wf = Workflow(name="su")
        wf.suspend("Waiting for approval")
        assert len(wf.nodes) == 1
        assert wf.nodes[0].node_type == NodeType.SUSPEND
        assert wf.nodes[0].message == "Waiting for approval"

    def test_fluent_chain_complex(self):
        wf = Workflow(name="complex")
        wf.then(double_step).parallel([add_one_step, negate_step]).then(double_step)
        assert len(wf.nodes) == 3
        assert wf.nodes[0].node_type == NodeType.SEQUENTIAL
        assert wf.nodes[1].node_type == NodeType.PARALLEL
        assert wf.nodes[2].node_type == NodeType.SEQUENTIAL

    def test_workflow_validates_empty(self):
        wf = Workflow(name="empty")
        assert len(wf.nodes) == 0
