"""Tests for embeddings builtin plugin."""

import pytest
from embeddings.schemas import EmbeddingRequest, EmbeddingResult


def test_embedding_request_single():
    req = EmbeddingRequest(input="hello world")
    assert req.input == "hello world"
    assert req.model_ref is None


def test_embedding_request_batch():
    req = EmbeddingRequest(
        input=["hello", "world"], model_ref="openai/text-embedding-3-small"
    )
    assert len(req.input) == 2
    assert req.model_ref == "openai/text-embedding-3-small"


def test_embedding_result():
    result = EmbeddingResult(
        vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        model_ref="openai/text-embedding-3-small",
        dimensions=3,
        duration_ms=50.0,
    )
    assert len(result.vectors) == 2
    assert result.dimensions == 3


async def test_plugin_setup_registers_category():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="embeddings",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "embedding:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="embeddings:EmbeddingsPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("embeddings")
    assert "embedding" in m._registry
    assert "before_embed" in m.hooks._specs
    assert "after_embed" in m.hooks._specs
