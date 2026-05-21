"""Verify RAG plugin is compatible with existing vectorstore_support schemas."""

import pytest
from machine_core.plugins.vectorstore_support.schemas import (
    SearchResult,
    UpsertRequest,
    SearchRequest,
)
from machine_core.plugins.rag_support.models import RankedResult


def test_search_result_used_by_reranker():
    """SearchResult from vectorstore_support is accepted by reranker."""
    sr = SearchResult(id="1", text="hello", score=0.9, metadata={"k": "v"})
    ranked = RankedResult(
        id=sr.id,
        text=sr.text or "",
        original_score=sr.score,
        rerank_score=0.95,
        metadata=sr.metadata,
    )
    assert ranked.original_score == 0.9
    assert ranked.rerank_score == 0.95


def test_upsert_request_for_tool_storage():
    """UpsertRequest can store tool descriptions for RAG filtering."""
    req = UpsertRequest(
        id="createInvoice",
        vector=[0.1, 0.2],
        text="Create an invoice for a customer",
        metadata={"source": "openapi", "operationId": "createInvoice"},
    )
    assert req.metadata["source"] == "openapi"


def test_search_request_with_table():
    """SearchRequest supports table selection for multi-collection RAG."""
    req = SearchRequest(
        query_vector=[0.1, 0.2],
        top_k=5,
        table="rag_documents",
    )
    assert req.table == "rag_documents"
