"""Tool search processor — RAG-based tool discovery wrapper.

Wraps an async search function (typically backed by the existing tool_filter.py
or a LanceDB vector store) to add relevant tools to the metadata for the agent.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ..base import Processor, ProcessorData, ProcessorResult

# Type for the search callback
SearchFn = Callable[[str, int], Awaitable[list[dict[str, Any]]]]


class ToolSearchProcessor(Processor):
    """Discover relevant tools via semantic search and add to metadata.

    Args:
        search_fn: Async function (query, top_k) -> list of tool dicts.
        top_k: Number of tools to retrieve.
    """

    name = "tool_search"
    type = "input"

    def __init__(self, search_fn: SearchFn, top_k: int = 10) -> None:
        self._search_fn = search_fn
        self.top_k = top_k

    async def process(self, data: ProcessorData) -> ProcessorResult:
        """Search for relevant tools and add to metadata."""
        tools = await self._search_fn(data.text, self.top_k)
        new_meta = {**data.metadata, "relevant_tools": tools}
        return data.replace(metadata=new_meta)
