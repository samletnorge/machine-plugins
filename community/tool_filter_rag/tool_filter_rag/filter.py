"""RAG-based tool filtering."""

from __future__ import annotations

from typing import Any

from embeddings.schemas import EmbeddingRequest, EmbeddingResult
from tool_support.schemas import ToolDefinition
from vectorstore_support.schemas import (
    SearchRequest,
    SearchResult,
    UpsertRequest,
)

TOOLS_TABLE = "tools"


class ToolFilterManager:
    def __init__(self, embedder: Any, store: Any) -> None:
        self._embedder = embedder
        self._store = store

    async def index_tools(self, tools: list[ToolDefinition]) -> None:
        if not tools:
            return
        descriptions = [_tool_index_text(t) for t in tools]
        embed_result: EmbeddingResult = await self._embedder.embed(
            EmbeddingRequest(input=descriptions)
        )
        records = [
            UpsertRequest(
                id=tool.name,
                vector=vector,
                text=description,
                metadata={"name": tool.name, "description": tool.description},
                table=TOOLS_TABLE,
            )
            for tool, vector, description in zip(
                tools, embed_result.vectors, descriptions
            )
        ]
        await self._store.upsert(records)

    async def filter(self, prompt: str, top_k: int = 10) -> list[SearchResult]:
        if not prompt.strip():
            return []
        embed_result: EmbeddingResult = await self._embedder.embed(
            EmbeddingRequest(input=prompt)
        )
        return await self._store.search(
            SearchRequest(
                query_vector=embed_result.vectors[0],
                top_k=top_k,
                table=TOOLS_TABLE,
            )
        )


def _tool_index_text(tool: ToolDefinition) -> str:
    metadata = tool.metadata or {}
    parts = [tool.name, tool.description]

    if metadata.get("method") and metadata.get("path"):
        parts.append(f"{metadata['method']} {metadata['path']}")

    if metadata.get("operation_summary"):
        parts.append(str(metadata["operation_summary"]))

    if metadata.get("operation_description"):
        parts.append(str(metadata["operation_description"]))

    parameter_lines = []
    for name, schema in (tool.parameters or {}).get("properties", {}).items():
        line = f"parameter {name}"
        if isinstance(schema, dict):
            if schema.get("type"):
                line += f" type {schema['type']}"
            if schema.get("description"):
                line += f" description {schema['description']}"
        parameter_lines.append(line)

    for detail in metadata.get("parameter_details", []):
        line = f"parameter {detail.get('name', '')} in {detail.get('in', 'query')}"
        if detail.get("required"):
            line += " required"
        if detail.get("description"):
            line += f" description {detail['description']}"
        schema = detail.get("schema", {})
        if isinstance(schema, dict) and schema.get("type"):
            line += f" type {schema['type']}"
        parameter_lines.append(line)

    required = (tool.parameters or {}).get("required", [])
    if required:
        parameter_lines.append(f"required parameters: {', '.join(required)}")

    parts.extend(parameter_lines)
    return "\n".join(part for part in parts if part)
