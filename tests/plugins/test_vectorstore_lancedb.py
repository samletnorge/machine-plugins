"""Tests for vectorstore-lancedb plugin."""

import json
from unittest.mock import MagicMock

import pytest

from vectorstore_support.schemas import (
    SearchRequest,
    SearchResult,
    UpsertRequest,
)


class TestLanceDBStore:
    @pytest.fixture
    def store(self, tmp_path):
        lancedb = pytest.importorskip("lancedb")  # noqa: F841
        from vectorstore_lancedb.store import LanceDBVectorStore

        return LanceDBVectorStore(db_path=str(tmp_path / "test_db"))

    async def test_upsert_creates_table(self, store):
        request = UpsertRequest(
            id="doc-1",
            vector=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
            text="hello",
            table="docs",
        )
        await store.upsert([request])
        from vectorstore_lancedb.store import _table_names

        assert "docs" in _table_names(store._db)

    async def test_upsert_adds_to_existing_table(self, store):
        r1 = UpsertRequest(
            id="doc-1", vector=[0.1, 0.2, 0.3], text="first", table="docs"
        )
        r2 = UpsertRequest(
            id="doc-2", vector=[0.4, 0.5, 0.6], text="second", table="docs"
        )
        await store.upsert([r1])
        await store.upsert([r2])
        tbl = store._db.open_table("docs")
        assert len(tbl.to_pandas()) == 2

    async def test_search_returns_results(self, store):
        r = UpsertRequest(
            id="doc-1", vector=[0.1, 0.2, 0.3], text="hello", table="docs"
        )
        await store.upsert([r])
        request = SearchRequest(query_vector=[0.1, 0.2, 0.3], top_k=5, table="docs")
        results = await store.search(request)
        assert len(results) == 1
        assert results[0].id == "doc-1"
        assert results[0].text == "hello"

    async def test_search_missing_table_returns_empty(self, store):
        request = SearchRequest(
            query_vector=[0.1, 0.2, 0.3], top_k=5, table="nonexistent"
        )
        results = await store.search(request)
        assert results == []

    async def test_get_stats(self, store):
        r = UpsertRequest(id="doc-1", vector=[0.1, 0.2, 0.3], table="docs")
        await store.upsert([r])
        stats = await store.get_stats()
        assert "docs" in stats["tables"]
        assert stats["table_count"] >= 1

    async def test_invoke_search(self, store):
        r = UpsertRequest(id="doc-1", vector=[0.1, 0.2, 0.3], text="hi", table="t")
        await store.upsert([r])
        request = SearchRequest(query_vector=[0.1, 0.2, 0.3], top_k=5, table="t")
        results = await store.invoke(request)
        assert len(results) == 1

    async def test_invoke_upsert(self, store):
        records = [UpsertRequest(id="doc-1", vector=[0.1, 0.2, 0.3], table="t")]
        await store.invoke(records)
        from vectorstore_lancedb.store import _table_names

        assert "t" in _table_names(store._db)

    async def test_invoke_bad_type(self, store):
        with pytest.raises(TypeError):
            await store.invoke("bad")
