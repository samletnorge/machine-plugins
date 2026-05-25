"""Task 13: Inngest-style adapter tests."""

import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel

from workflow_support.adapters.base import ExternalEngineAdapter
from workflow_support.adapters.inngest import InngestAdapter
from workflow_support.workflow import Workflow
from workflow_support.step import step, StepContext


class Val(BaseModel):
    value: int


@step(name="double", input_schema=Val, output_schema=Val)
async def double(ctx: StepContext) -> Val:
    return Val(value=ctx.input_data.value * 2)


class TestExternalEngineAdapter:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            ExternalEngineAdapter()  # type: ignore


class TestInngestAdapter:
    def test_implements_interface(self):
        adapter = InngestAdapter(base_url="http://localhost:8288")
        assert isinstance(adapter, ExternalEngineAdapter)

    def test_register_workflow(self):
        adapter = InngestAdapter(base_url="http://localhost:8288")
        wf = Workflow(name="test-wf")
        wf.then(double)
        adapter.register_workflow(wf)
        assert "test-wf" in adapter.registered_workflows

    def test_build_function_config(self):
        adapter = InngestAdapter(base_url="http://localhost:8288")
        wf = Workflow(name="price-scraper")
        wf.then(double)
        adapter.register_workflow(wf)
        config = adapter.build_function_config("price-scraper")
        assert config["id"] == "price-scraper"
        assert "steps" in config

    @pytest.mark.asyncio
    async def test_trigger_generates_event(self):
        adapter = InngestAdapter(base_url="http://localhost:8288")
        wf = Workflow(name="test-wf")
        wf.then(double)
        adapter.register_workflow(wf)

        with patch.object(adapter, "_send_event", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"event_id": "evt_123"}
            result = await adapter.trigger("test-wf", data={"value": 5})
            assert result["event_id"] == "evt_123"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_unregistered_raises(self):
        adapter = InngestAdapter(base_url="http://localhost:8288")
        with pytest.raises(KeyError, match="unknown"):
            await adapter.trigger("unknown", data={})
