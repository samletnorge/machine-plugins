"""Tests for tool search processor (RAG-based tool discovery wrapper)."""

import pytest
from machine_core.plugins.processor_support.base import ProcessorData
from machine_core.plugins.processor_support.builtin.tool_search import (
    ToolSearchProcessor,
)


async def _mock_search(query: str, top_k: int) -> list[dict]:
    all_tools = [
        {"name": "get_weather", "description": "Get weather forecast"},
        {"name": "search_stations", "description": "Search fuel stations"},
        {"name": "calculate", "description": "Math calculator"},
    ]
    # Simple keyword overlap match for testing
    query_words = set(query.lower().split())
    return [
        t for t in all_tools if query_words & set(t["description"].lower().split())
    ][:top_k]


@pytest.mark.asyncio
async def test_tool_search_adds_tools_to_metadata():
    proc = ToolSearchProcessor(search_fn=_mock_search, top_k=5)
    data = ProcessorData(text="What's the weather like?")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert "relevant_tools" in result.metadata
    assert len(result.metadata["relevant_tools"]) == 1
    assert result.metadata["relevant_tools"][0]["name"] == "get_weather"


@pytest.mark.asyncio
async def test_tool_search_no_results():
    proc = ToolSearchProcessor(search_fn=_mock_search, top_k=5)
    data = ProcessorData(text="Tell me a joke")
    result = await proc.process(data)
    assert isinstance(result, ProcessorData)
    assert result.metadata.get("relevant_tools") == []


@pytest.mark.asyncio
async def test_tool_search_respects_top_k():
    async def many_results(query: str, top_k: int) -> list[dict]:
        return [{"name": f"tool_{i}", "description": f"Tool {i}"} for i in range(top_k)]

    proc = ToolSearchProcessor(search_fn=many_results, top_k=3)
    data = ProcessorData(text="anything")
    result = await proc.process(data)
    assert len(result.metadata["relevant_tools"]) == 3


@pytest.mark.asyncio
async def test_tool_search_preserves_text():
    proc = ToolSearchProcessor(search_fn=_mock_search, top_k=5)
    data = ProcessorData(text="Search fuel stations nearby")
    result = await proc.process(data)
    assert result.text == "Search fuel stations nearby"
