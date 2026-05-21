"""Task 14: Temporal-style adapter tests."""

import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel

from machine_core.plugins.workflow_support.adapters.temporal import TemporalAdapter
from machine_core.plugins.workflow_support.adapters.base import ExternalEngineAdapter
from machine_core.plugins.workflow_support.workflow import Workflow
from machine_core.plugins.workflow_support.step import step, StepContext


class Val(BaseModel):
    value: int


@step(name="double", input_schema=Val, output_schema=Val)
async def double(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value * 2)


class TestTemporalAdapter:
    def test_implements_interface(self):
        adapter = TemporalAdapter(endpoint="localhost:7233", namespace="default")
        assert isinstance(adapter, ExternalEngineAdapter)

    def test_register_workflow(self):
        adapter = TemporalAdapter(endpoint="localhost:7233", namespace="default")
        wf = Workflow(name="durable-wf")
        wf.then(double)
        adapter.register_workflow(wf)
        assert "durable-wf" in adapter.registered_workflows

    def test_build_function_config(self):
        adapter = TemporalAdapter(endpoint="localhost:7233", namespace="default")
        wf = Workflow(name="durable-wf")
        wf.then(double)
        adapter.register_workflow(wf)
        config = adapter.build_function_config("durable-wf")
        assert config["workflow_type"] == "durable-wf"
        assert config["namespace"] == "default"
        assert "activities" in config

    @pytest.mark.asyncio
    async def test_trigger_calls_start_workflow(self):
        adapter = TemporalAdapter(endpoint="localhost:7233", namespace="default")
        wf = Workflow(name="durable-wf")
        wf.then(double)
        adapter.register_workflow(wf)

        with patch.object(
            adapter, "_start_workflow_execution", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"run_id": "run_abc123", "workflow_id": "durable-wf"}
            result = await adapter.trigger("durable-wf", data={"value": 10})
            assert result["run_id"] == "run_abc123"
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_unregistered_raises(self):
        adapter = TemporalAdapter(endpoint="localhost:7233", namespace="default")
        with pytest.raises(KeyError):
            await adapter.trigger("nope", data={})
