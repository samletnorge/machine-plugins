from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent_support.schemas import AgentDefinition, AgentRunResult
from vectorstore_support.schemas import SearchResult

from agent_brreg_expert.runner import BrregAgentRunner


@pytest.mark.asyncio
async def test_brreg_runner_only_passes_filter_selected_tools():
    filter_rag = AsyncMock()
    filter_rag.filter = AsyncMock(
        return_value=[
            SearchResult(
                id="hentEnhet",
                score=0.9,
                text="Hent enhet på organisasjonsnummer",
                metadata={"name": "hentEnhet"},
            )
        ]
    )

    basic_runner = AsyncMock()
    basic_runner.run = AsyncMock(
        return_value=AgentRunResult(agent_name="basic", output="ok", steps=[])
    )

    machine = SimpleNamespace(
        resolve=lambda category, name: {
            ("rag_pipeline", "brreg-companies"): None,
            ("tool", "__filter_rag__"): filter_rag,
            ("agent", "basic"): basic_runner,
        }.get((category, name)),
        list_category=lambda category: {
            "tool": {
                "brreg_hentEnhet": SimpleNamespace(name="hentEnhet"),
                "brreg_hentEnheter": SimpleNamespace(name="hentEnheter"),
            }
        }.get(category, {}),
    )

    runner = BrregAgentRunner(machine=machine, config={"tool_filter_top_k": 5})

    await runner.run(
        input="finn bedrift",
        definition=AgentDefinition(name="brreg-expert", description="test"),
    )

    passed_tools = basic_runner.run.call_args.kwargs["tools"]
    assert [tool.name for tool in passed_tools] == ["hentEnhet"]


@pytest.mark.asyncio
async def test_brreg_runner_defaults_tool_filter_top_k_to_100():
    filter_rag = AsyncMock()
    filter_rag.filter = AsyncMock(return_value=[])

    basic_runner = AsyncMock()
    basic_runner.run = AsyncMock(
        return_value=AgentRunResult(agent_name="basic", output="ok", steps=[])
    )

    machine = SimpleNamespace(
        resolve=lambda category, name: {
            ("rag_pipeline", "brreg-companies"): None,
            ("tool", "__filter_rag__"): filter_rag,
            ("agent", "basic"): basic_runner,
        }.get((category, name)),
        list_category=lambda category: {} if category == "tool" else {},
    )

    runner = BrregAgentRunner(machine=machine, config={})

    await runner.run(
        input="finn bedrift på navn",
        definition=AgentDefinition(name="brreg-expert", description="test"),
    )

    assert filter_rag.filter.await_args.kwargs["top_k"] == 100


def test_brreg_manifest_defaults_tool_filter_top_k_to_100():
    import json
    from pathlib import Path

    manifest_path = (
        Path(__file__).resolve().parents[2]
        / "community"
        / "agent_brreg_expert"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())

    assert manifest["config_schema"]["tool_filter_top_k"]["default"] == 100
