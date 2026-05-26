"""Tests for pipeline.py — BrregPipeline ingest + retrieve."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agent_brreg_expert.pipeline import BrregPipeline


@pytest.fixture
def mock_machine():
    """Create a mock machine with all necessary resolvers."""
    machine = MagicMock()

    # Mock embedder
    embedder = AsyncMock()
    embedder.embed = AsyncMock(return_value=MagicMock(vectors=[[0.1] * 4096]))

    # Mock vectorstore
    vectorstore = AsyncMock()
    vectorstore.upsert = AsyncMock()
    vectorstore.search = AsyncMock(
        return_value=[
            MagicMock(
                id="123_0",
                score=0.9,
                text='{"navn": "Equinor"}',
                metadata={"org_nr": "123"},
            ),
            MagicMock(
                id="456_0",
                score=0.7,
                text='{"navn": "DNB"}',
                metadata={"org_nr": "456"},
            ),
        ]
    )

    # Mock chunker
    chunker = MagicMock()
    chunker.chunk = MagicMock(
        return_value=[
            MagicMock(text='{"navn": "TestAS"}', index=0, metadata={}),
        ]
    )

    # Mock extractors
    summary_extractor = AsyncMock()
    summary_extractor.extract = AsyncMock(
        return_value=MagicMock(summary="TestAS is a Norwegian company.")
    )

    keywords_extractor = AsyncMock()
    keywords_extractor.extract = AsyncMock(
        return_value=MagicMock(keywords=["technology", "oslo"])
    )

    # Mock reranker
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(
        return_value=[
            MagicMock(
                id="123_0",
                text='{"navn": "Equinor"}',
                rerank_score=0.95,
                metadata={"org_nr": "123"},
            ),
        ]
    )

    def resolve(category, name):
        mapping = {
            ("embedding", "ollama"): embedder,
            ("vector_store", "lancedb"): vectorstore,
            ("chunker", "json"): chunker,
            ("metadata_extractor", "summary"): summary_extractor,
            ("metadata_extractor", "keywords"): keywords_extractor,
            ("reranker", "llm"): reranker,
        }
        return mapping.get((category, name))

    machine.resolve = resolve
    return machine


@pytest.fixture
def config():
    return {
        "vectorstore_table": "brreg_companies",
        "retrieve_top_k": 20,
        "rerank_top_k": 5,
    }


@pytest.mark.asyncio
async def test_retrieve(mock_machine, config):
    """Retrieve embeds query, searches vectorstore, reranks."""
    pipeline = BrregPipeline(machine=mock_machine, config=config)
    results = await pipeline.retrieve(query="Hvem eier Equinor?")

    # Should call embed, search, rerank
    mock_machine.resolve("embedding", "ollama").embed.assert_called_once()
    mock_machine.resolve("vector_store", "lancedb").search.assert_called_once()
    mock_machine.resolve("reranker", "llm").rerank.assert_called_once()
    assert len(results) == 1


@pytest.mark.asyncio
async def test_retrieve_no_reranker(mock_machine, config):
    """Retrieve works without reranker (returns raw results)."""
    # Remove reranker
    original_resolve = mock_machine.resolve

    def resolve_no_reranker(category, name):
        if category == "reranker":
            return None
        return original_resolve(category, name)

    mock_machine.resolve = resolve_no_reranker

    pipeline = BrregPipeline(machine=mock_machine, config=config)
    results = await pipeline.retrieve(query="test")
    assert len(results) == 2  # raw results, no reranking


@pytest.mark.asyncio
async def test_ingest_processes_merged_docs(mock_machine, config):
    """Ingest downloads, merges, chunks, extracts, embeds, upserts."""
    pipeline = BrregPipeline(machine=mock_machine, config=config)

    with (
        patch(
            "agent_brreg_expert.pipeline.download_entities", new_callable=AsyncMock
        ) as dl_ent,
        patch(
            "agent_brreg_expert.pipeline.download_sub_entities", new_callable=AsyncMock
        ) as dl_sub,
        patch(
            "agent_brreg_expert.pipeline.download_roles", new_callable=AsyncMock
        ) as dl_roles,
        patch(
            "agent_brreg_expert.pipeline.download_frivillig", new_callable=AsyncMock
        ) as dl_friv,
        patch(
            "agent_brreg_expert.pipeline.download_parti", new_callable=AsyncMock
        ) as dl_parti,
    ):
        dl_ent.return_value = [{"organisasjonsnummer": "123", "navn": "TestAS"}]
        dl_sub.return_value = []
        dl_roles.return_value = []
        dl_friv.return_value = []
        dl_parti.return_value = []

        result = await pipeline.ingest()

        assert result["status"] == "completed"
        assert result["documents_processed"] == 1
        # Vectorstore upsert should have been called
        mock_machine.resolve("vector_store", "lancedb").upsert.assert_called()
