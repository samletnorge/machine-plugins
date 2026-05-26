"""Tests for RagSupportPlugin registration."""

import pytest
from unittest.mock import MagicMock
from rag_support import RagSupportPlugin


def test_plugin_class_exists():
    plugin = RagSupportPlugin()
    assert hasattr(plugin, "initialize")
    assert hasattr(plugin, "setup")
    assert hasattr(plugin, "shutdown")


async def test_plugin_registers_categories_standalone():
    """Test that setup registers categories and standalone chunkers (no config)."""
    plugin = RagSupportPlugin()

    registered_categories = []
    registered_items = []

    class MockCtx:
        _machine = MagicMock()

        def register_category(self, name, **kwargs):
            registered_categories.append(name)

        def register(self, category, name, impl):
            registered_items.append((category, name))

    # No config — only standalone components register
    await plugin.setup(MockCtx())

    assert "chunker" in registered_categories
    assert "reranker" in registered_categories
    assert "metadata_extractor" in registered_categories
    assert "rag_pipeline" in registered_categories

    # 7 standalone chunkers (no semantic — needs embedder config)
    chunker_names = [name for cat, name in registered_items if cat == "chunker"]
    assert "recursive" in chunker_names
    assert "sentence" in chunker_names
    assert "token" in chunker_names
    assert "markdown" in chunker_names
    assert "html" in chunker_names
    assert "json" in chunker_names
    assert "code" in chunker_names
    assert "semantic" not in chunker_names

    # No rerankers or extractors without config
    reranker_names = [name for cat, name in registered_items if cat == "reranker"]
    assert reranker_names == []
    extractor_names = [
        name for cat, name in registered_items if cat == "metadata_extractor"
    ]
    assert extractor_names == []


async def test_plugin_registers_llm_components_with_config():
    """Test that LLM-dependent components register when config provides provider."""
    plugin = RagSupportPlugin()
    await plugin.initialize(
        config={
            "reranker_llm": {"provider": "ollama", "model": "gemma4:latest"},
            "extractor_llm": {"provider": "ollama", "model": "gemma4:latest"},
        }
    )

    registered_items = []
    mock_provider = MagicMock()

    class MockMachine:
        def resolve(self, category, name):
            if category == "model_provider" and name == "ollama":
                return mock_provider
            return None

    class MockCtx:
        _machine = MockMachine()

        def register_category(self, name, **kwargs):
            pass

        def register(self, category, name, impl):
            registered_items.append((category, name))

    await plugin.setup(MockCtx())

    reranker_names = [name for cat, name in registered_items if cat == "reranker"]
    assert "llm" in reranker_names

    extractor_names = [
        name for cat, name in registered_items if cat == "metadata_extractor"
    ]
    assert "title" in extractor_names
    assert "summary" in extractor_names
    assert "keywords" in extractor_names
    assert "questions" in extractor_names


async def test_plugin_registers_semantic_chunker_with_config():
    """Test that semantic chunker registers when embedder config is provided."""
    plugin = RagSupportPlugin()
    await plugin.initialize(
        config={
            "semantic_chunker": {
                "provider": "ollama",
                "model": "qwen3-embedding:8b:latest",
            },
        }
    )

    registered_items = []
    mock_embedder = MagicMock()

    class MockMachine:
        def resolve(self, category, name):
            if category == "embedding" and name == "ollama":
                return mock_embedder
            return None

    class MockCtx:
        _machine = MockMachine()

        def register_category(self, name, **kwargs):
            pass

        def register(self, category, name, impl):
            registered_items.append((category, name))

    await plugin.setup(MockCtx())

    chunker_names = [name for cat, name in registered_items if cat == "chunker"]
    assert "semantic" in chunker_names
