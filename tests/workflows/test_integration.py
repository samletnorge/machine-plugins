"""Task 15: Integration test — full workflow lifecycle including nested workflows,
agent steps, persistence, and evented execution."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from pydantic import BaseModel

from machine_core.plugins.workflow_support.step import step, StepContext
from machine_core.plugins.workflow_support.workflow import Workflow
from machine_core.plugins.workflow_support.run import RunStatus
from machine_core.plugins.workflow_support.engine import DefaultExecutionEngine
from machine_core.plugins.workflow_support.events import (
    EventedExecutionEngine,
    WorkflowEvent,
)
from machine_core.plugins.workflow_support.persistence import JsonRunStore
from machine_core.plugins.workflow_support.agent_step import agent_as_step
from machine_core.plugins.workflow_support.nested import workflow_as_step
from machine_core.plugins.workflow_support.network import (
    AgentNetwork,
    NetworkAgent,
    DelegationConfig,
)


# --- Models ---
class PriceInput(BaseModel):
    station_id: str
    value: int = 0


class PriceOutput(BaseModel):
    station_id: str
    price: float


class ValidationResult(BaseModel):
    station_id: str
    price: float
    valid: bool


class EnrichedPrice(BaseModel):
    station_id: str
    price: float
    chain: str


class StoreResult(BaseModel):
    station_id: str
    stored: bool


# --- Steps ---
@step(name="fetch-price", input_schema=PriceInput, output_schema=PriceOutput)
async def fetch_price(ctx: StepContext) -> PriceOutput:
    return PriceOutput(station_id=ctx.input_data.station_id, price=19.95)


@step(name="validate-price", input_schema=PriceOutput, output_schema=ValidationResult)
async def validate_price(ctx: StepContext) -> ValidationResult:
    return ValidationResult(
        station_id=ctx.input_data.station_id,
        price=ctx.input_data.price,
        valid=ctx.input_data.price > 0,
    )


@step(name="enrich-price", input_schema=PriceOutput, output_schema=EnrichedPrice)
async def enrich_price(ctx: StepContext) -> EnrichedPrice:
    return EnrichedPrice(
        station_id=ctx.input_data.station_id,
        price=ctx.input_data.price,
        chain="Circle K",
    )


@step(name="store-price", input_schema=PriceOutput, output_schema=StoreResult)
async def store_price(ctx: StepContext) -> StoreResult:
    return StoreResult(station_id=ctx.input_data.station_id, stored=True)


class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_sequential_workflow_with_persistence(self, tmp_path: Path):
        """Run a workflow, persist state, reload and verify."""
        wf = Workflow(name="price-pipeline")
        wf.then(fetch_price).then(validate_price)

        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=PriceInput(station_id="ST001"))

        assert run.status == RunStatus.COMPLETED
        assert run.output.valid is True

        # Persist
        store = JsonRunStore(directory=tmp_path)
        store.save(run)

        # Reload
        loaded = store.load(run.run_id)
        assert loaded.workflow_name == "price-pipeline"
        assert loaded.status == RunStatus.COMPLETED
        assert len(loaded.step_results) == 2

    @pytest.mark.asyncio
    async def test_evented_workflow_emits_all_events(self):
        events: list[WorkflowEvent] = []

        wf = Workflow(name="evented-pipeline")
        wf.then(fetch_price).then(validate_price)

        engine = EventedExecutionEngine()
        engine.on_event(lambda e: events.append(e))
        run = await engine.execute(wf, input_data=PriceInput(station_id="ST002"))

        assert run.status == RunStatus.COMPLETED
        types = [e.event_type for e in events]
        assert types[0] == "workflow_started"
        assert types[-1] == "workflow_completed"
        assert types.count("step_started") == 2
        assert types.count("step_completed") == 2

    @pytest.mark.asyncio
    async def test_parallel_then_sequential(self):
        wf = Workflow(name="par-pipeline")
        wf.then(fetch_price).parallel([validate_price, enrich_price]).then(store_price)

        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=PriceInput(station_id="ST003"))

        assert run.status == RunStatus.COMPLETED
        assert len(run.step_results) == 4  # fetch, validate, enrich, store

    @pytest.mark.asyncio
    async def test_nested_workflow(self):
        inner = Workflow(name="validate-enrich")
        inner.then(validate_price)

        inner_step = workflow_as_step(
            inner, input_schema=PriceOutput, output_schema=ValidationResult
        )

        outer = Workflow(name="full-pipeline")
        outer.then(fetch_price).then(inner_step)

        engine = DefaultExecutionEngine()
        run = await engine.execute(outer, input_data=PriceInput(station_id="ST004"))
        assert run.status == RunStatus.COMPLETED
        assert run.output.valid is True

    @pytest.mark.asyncio
    async def test_agent_as_step_in_workflow(self):
        mock_agent = AsyncMock()
        mock_agent.name = "price-analyst"
        mock_agent.run = AsyncMock(
            return_value=PriceOutput(station_id="ST005", price=21.50)
        )

        agent_step_inst = agent_as_step(
            agent=mock_agent,
            input_schema=PriceInput,
            output_schema=PriceOutput,
        )

        wf = Workflow(name="agent-pipeline")
        wf.then(agent_step_inst).then(validate_price)

        engine = DefaultExecutionEngine()
        run = await engine.execute(wf, input_data=PriceInput(station_id="ST005"))
        assert run.status == RunStatus.COMPLETED
        assert run.output.valid is True

    @pytest.mark.asyncio
    async def test_suspend_resume_full_lifecycle(self, tmp_path: Path):
        wf = Workflow(name="approval-pipeline")
        wf.then(fetch_price).suspend("Approve price update?").then(store_price)

        engine = DefaultExecutionEngine()
        store = JsonRunStore(directory=tmp_path)

        # Execute — suspends
        run = await engine.execute(wf, input_data=PriceInput(station_id="ST006"))
        assert run.status == RunStatus.SUSPENDED
        store.save(run)

        # Simulate: human approves, resume
        loaded = store.load(run.run_id)
        loaded.resume(resume_data={"approved": True})
        loaded.current_node_index = loaded.suspended_at_node + 1
        last_output = PriceOutput(**loaded.step_results[-1].output)
        loaded = await engine.execute(wf, input_data=last_output, run=loaded)

        assert loaded.status == RunStatus.COMPLETED
        assert loaded.output.stored is True
        store.save(loaded)

    @pytest.mark.asyncio
    async def test_agent_network_delegation(self):
        delegation_log: list[str] = []

        async def on_start(name: str, task: str) -> bool:
            delegation_log.append(f"start:{name}")
            return True

        async def on_complete(name: str, result) -> None:
            delegation_log.append(f"complete:{name}")

        config = DelegationConfig(
            on_delegation_start=on_start,
            on_delegation_complete=on_complete,
        )
        network = AgentNetwork(name="price-network", delegation_config=config)

        fetcher = AsyncMock()
        fetcher.name = "fetcher"
        fetcher.run = AsyncMock(
            return_value=PriceOutput(station_id="ST007", price=18.50)
        )

        validator = AsyncMock()
        validator.name = "validator"
        validator.run = AsyncMock(
            return_value=ValidationResult(station_id="ST007", price=18.50, valid=True)
        )

        network.register(
            NetworkAgent(
                agent=fetcher, description="Fetches prices", capabilities=["http"]
            )
        )
        network.register(
            NetworkAgent(
                agent=validator,
                description="Validates data",
                capabilities=["validation"],
            )
        )

        # Delegate
        price = await network.delegate("fetcher", PriceInput(station_id="ST007"))
        assert price.price == 18.50

        validation = await network.delegate("validator", price)
        assert validation.valid is True

        assert delegation_log == [
            "start:fetcher",
            "complete:fetcher",
            "start:validator",
            "complete:validator",
        ]

        # Tools export
        tools = network.as_tools()
        assert len(tools) == 2

    @pytest.mark.asyncio
    async def test_branch_workflow(self):
        def is_expensive(state: dict) -> bool:
            return state.get("last_value", 0) > 20

        @step(
            name="flag-expensive", input_schema=PriceOutput, output_schema=StoreResult
        )
        async def flag_expensive(ctx: StepContext) -> StoreResult:
            return StoreResult(station_id=ctx.input_data.station_id, stored=False)

        wf = Workflow(name="branch-pipeline")
        wf.then(fetch_price).branch(
            is_expensive, {True: flag_expensive, False: store_price}
        )

        engine = DefaultExecutionEngine()
        run = await engine.execute(
            wf,
            input_data=PriceInput(station_id="ST008"),
            initial_state={"last_value": 19.95},
        )
        assert run.status == RunStatus.COMPLETED
