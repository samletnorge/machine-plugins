"""Integration tests for Batch 3: vectorstore + openapi + rag filter."""

import pytest
from machine_core import Machine


@pytest.mark.asyncio
async def test_vectorstore_category_exists():
    m = Machine()
    await m.start()
    assert "vector_store" in m._registry
    await m.shutdown()


@pytest.mark.asyncio
async def test_all_batch3_manifests_discovered():
    from machine_core.plugins import builtin_manifests

    manifests = {m.name: m for m in builtin_manifests()}
    expected = [
        "vectorstore-support",
        "vectorstore-lancedb",
        "tool-openapi",
        "tool-filter-rag",
    ]
    for name in expected:
        assert name in manifests, f"Missing manifest: {name}"
