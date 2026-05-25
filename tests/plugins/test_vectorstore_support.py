"""Tests for vectorstore-support category plugin."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from vectorstore_support.schemas import (
    VectorStoreConfig,
    SearchRequest,
    SearchResult,
    UpsertRequest,
)


def test_vectorstore_config_valid():
    cfg = VectorStoreConfig(name="lancedb", dimensions=768)
    assert cfg.name == "lancedb"
    assert cfg.distance_metric == "cosine"


def test_vectorstore_config_custom_metric():
    cfg = VectorStoreConfig(name="lancedb", dimensions=768, distance_metric="l2")
    assert cfg.distance_metric == "l2"


def test_search_request_valid():
    req = SearchRequest(query_vector=[0.1, 0.2, 0.3], top_k=5)
    assert len(req.query_vector) == 3
    assert req.filter is None


def test_search_request_with_filter():
    req = SearchRequest(
        query_vector=[0.1, 0.2],
        top_k=10,
        filter={"source": "docs"},
        table="knowledge",
    )
    assert req.filter == {"source": "docs"}
    assert req.table == "knowledge"


def test_search_result_valid():
    r = SearchResult(id="abc", score=0.95, text="hello")
    assert r.score == 0.95
    assert r.metadata == {}


def test_upsert_request_valid():
    req = UpsertRequest(
        id="doc-1",
        vector=[0.1, 0.2, 0.3],
        metadata={"source": "test"},
        text="hello world",
        table="docs",
    )
    assert req.table == "docs"


def test_upsert_request_minimal():
    req = UpsertRequest(id="doc-1", vector=[0.1, 0.2])
    assert req.metadata == {}
    assert req.text is None


async def test_vectorstore_category_registered():
    """vectorstore-support should register the 'vector_store' category."""
    from machine_core import Machine

    m = Machine()
    await m.start()
    assert "vector_store" in m._registry
    await m.shutdown()
