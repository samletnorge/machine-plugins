"""Integration tests for vectorstore, OpenAPI tools, and RAG tool filtering."""

from tests.conftest import discover_manifests


async def test_vectorstore_category_exists(machine_with_all_plugins):
    assert "vector_store" in machine_with_all_plugins.list_categories()


def test_all_batch3_manifests_discovered():
    manifests = {m.name for m in discover_manifests()}
    for name in (
        "vectorstore_support",
        "vectorstore_lancedb",
        "tool_openapi",
        "tool_filter_rag",
    ):
        assert name in manifests, f"Missing manifest: {name}"
