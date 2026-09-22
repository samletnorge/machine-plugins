"""Task 14: Temporal-style adapter tests."""

import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel

from workflow_support.adapters.temporal import TemporalAdapter
from workflow_support.adapters.base import ExternalEngineAdapter
from workflow_support.workflow import Workflow
from workflow_support.step import step, StepContext


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

    @pytest.mark.asyncio
    async def test_start_workflow_uses_temporal_client(self, monkeypatch):
        import sys
        import types

        class _FakeHandle:
            id = "durable-wf-abc"
            result_run_id = "run_1"

        class _FakeClient:
            started: list = []

            @classmethod
            async def connect(cls, endpoint, namespace=None):
                cls.endpoint = endpoint
                cls.namespace = namespace
                return cls()

            async def start_workflow(self, workflow, arg, id=None, task_queue=None):
                self.started.append((workflow, arg, id, task_queue))
                return _FakeHandle()

        temporalio = types.ModuleType("temporalio")
        client_mod = types.ModuleType("temporalio.client")
        client_mod.Client = _FakeClient
        temporalio.client = client_mod
        monkeypatch.setitem(sys.modules, "temporalio", temporalio)
        monkeypatch.setitem(sys.modules, "temporalio.client", client_mod)

        adapter = TemporalAdapter(endpoint="localhost:7233", namespace="default")
        wf = Workflow(name="durable-wf")
        wf.then(double)
        adapter.register_workflow(wf)

        result = await adapter.trigger("durable-wf", data={"value": 10})

        assert result["engine"] == "temporal"
        assert result["workflow_id"] == "durable-wf-abc"
        assert result["run_id"] == "run_1"
        assert _FakeClient.started[0][0] == "durable-wf"
        assert _FakeClient.started[0][3] == "machine-core-durable-wf"
        assert _FakeClient.endpoint == "localhost:7233"
