"""Tests for tool_filter_rag plugin."""

import pytest
from unittest.mock import AsyncMock

from tool_support.schemas import ToolDefinition
from embeddings.schemas import EmbeddingResult
from vectorstore_support.schemas import SearchResult


class TestToolFilterRAG:
    @pytest.fixture
    def mock_embedder(self):
        embedder = AsyncMock()
        embedder.embed.return_value = EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3]],
            model_ref="test-model",
            dimensions=3,
        )
        return embedder

    @pytest.fixture
    def mock_store(self):
        store = AsyncMock()
        store.search.return_value = [
            SearchResult(id="calculator", score=0.9, text="Math calculator"),
            SearchResult(id="weather", score=0.7, text="Get weather info"),
        ]
        return store

    @pytest.fixture
    def filter_manager(self, mock_embedder, mock_store):
        from tool_filter_rag.filter import ToolFilterManager

        return ToolFilterManager(embedder=mock_embedder, store=mock_store)

    @pytest.mark.asyncio
    async def test_index_tools(self, filter_manager, mock_embedder, mock_store):
        mock_embedder.embed.return_value = EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            model_ref="test-model",
            dimensions=3,
        )
        tools = [
            ToolDefinition(
                name="calculator",
                description="Math calculator",
                handler=lambda: None,
            ),
            ToolDefinition(
                name="weather",
                description="Get weather info",
                handler=lambda: None,
            ),
        ]
        await filter_manager.index_tools(tools)
        mock_store.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_tools_includes_rich_openapi_context(
        self, filter_manager, mock_embedder, mock_store
    ):
        mock_embedder.embed.return_value = EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3]],
            model_ref="test-model",
            dimensions=3,
        )
        tools = [
            ToolDefinition(
                name="hentEnheter",
                description="Hent enheter som matcher søke filtere",
                parameters={
                    "type": "object",
                    "properties": {
                        "navn": {"type": "string", "description": "Enhetens navn"},
                        "organisasjonsnummer": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Liste med organisasjonsnummer",
                        },
                    },
                    "required": ["navn"],
                },
                metadata={
                    "source": "openapi",
                    "method": "get",
                    "path": "/enhetsregisteret/api/enheter",
                    "operation_summary": "Hent enheter som matcher søke filtere",
                },
                handler=lambda: None,
            )
        ]

        await filter_manager.index_tools(tools)

        records = mock_store.upsert.call_args.args[0]
        assert len(records) == 1
        assert "navn" in records[0].text
        assert "organisasjonsnummer" in records[0].text
        assert "/enhetsregisteret/api/enheter" in records[0].text
        assert "get" in records[0].text.lower()

    @pytest.mark.asyncio
    async def test_filter_returns_relevant_tools(self, filter_manager):
        result = await filter_manager.filter("What is 2+2?", top_k=2)
        assert len(result) <= 2
        assert "calculator" in [r.id for r in result]

    @pytest.mark.asyncio
    async def test_filter_empty_prompt(self, filter_manager):
        result = await filter_manager.filter("", top_k=5)
        assert isinstance(result, list)
        assert len(result) == 0
