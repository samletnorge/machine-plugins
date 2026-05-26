"""Tests for embedding provider plugins (ollama, azure, google)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


class TestOllamaEmbeddingProvider:
    @pytest.fixture
    def provider(self):
        from embeddings_ollama.provider import (
            OllamaEmbeddingProvider,
        )

        return OllamaEmbeddingProvider(
            base_url="http://localhost:11434", model="qwen3-embedding:8b"
        )

    def _mock_response(self, vectors, model="qwen3-embedding:8b"):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "model": model,
            "data": [{"embedding": v} for v in vectors],
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
        return resp

    async def test_embed_single(self, provider):
        vectors = [[0.1, 0.2, 0.3]]
        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.post.return_value = self._mock_response(vectors)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await provider.embed(EmbeddingRequest(input="hello"))

        assert isinstance(result, EmbeddingResult)
        assert result.vectors == vectors
        assert result.dimensions == 3
        assert result.model_ref == "qwen3-embedding:8b"

    async def test_embed_batch(self, provider):
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.post.return_value = self._mock_response(vectors)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await provider.embed(EmbeddingRequest(input=["a", "b"]))

        assert len(result.vectors) == 2
        assert result.dimensions == 2


# ---------------------------------------------------------------------------
# Azure
# ---------------------------------------------------------------------------


class TestAzureEmbeddingProvider:
    @pytest.fixture
    def provider(self):
        from embeddings_azure.provider import (
            AzureEmbeddingProvider,
        )

        return AzureEmbeddingProvider(
            endpoint="https://myresource.openai.azure.com",
            api_key="test-key",
            deployment="text-embedding-ada-002",
        )

    async def test_embed(self, provider):
        vectors = [[0.1, 0.2, 0.3, 0.4]]
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "model": "text-embedding-ada-002",
            "data": [{"embedding": v} for v in vectors],
            "usage": {"prompt_tokens": 3, "total_tokens": 3},
        }

        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.post.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await provider.embed(EmbeddingRequest(input="test"))

        assert isinstance(result, EmbeddingResult)
        assert result.vectors == vectors
        assert result.dimensions == 4
        # Verify api-key header was used (not bearer)
        call_kwargs = client.post.call_args
        assert call_kwargs.kwargs["headers"]["api-key"] == "test-key"


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------


class TestGoogleEmbeddingProvider:
    async def test_embed(self):
        with patch("google.genai.Client") as MockGenAI:
            mock_client = MagicMock()
            MockGenAI.return_value = mock_client

            from embeddings_google.provider import (
                GoogleEmbeddingProvider,
            )

            provider = GoogleEmbeddingProvider(
                api_key="test-key", model="text-embedding-004", dimensions=768
            )

            # Mock embed_content response
            emb1 = MagicMock()
            emb1.values = [0.1, 0.2, 0.3]
            emb2 = MagicMock()
            emb2.values = [0.4, 0.5, 0.6]
            mock_response = MagicMock()
            mock_response.embeddings = [emb1, emb2]
            mock_client.models.embed_content.return_value = mock_response

            result = await provider.embed(EmbeddingRequest(input=["hello", "world"]))

        assert isinstance(result, EmbeddingResult)
        assert len(result.vectors) == 2
        assert result.vectors[0] == [0.1, 0.2, 0.3]
        assert result.dimensions == 3
        assert result.model_ref == "text-embedding-004"


# ---------------------------------------------------------------------------
# Manifest discovery
# ---------------------------------------------------------------------------


def test_all_embedding_manifests():
    """Check that all 3 embedding provider manifests are discoverable."""
    import pathlib

    plugins_dir = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "src"
        / "machine_core"
        / "plugins"
    )
    expected = {"embeddings_ollama", "embeddings_azure", "embeddings_google"}
    found = set()
    for manifest_path in plugins_dir.glob("embeddings_*/manifest.json"):
        with open(manifest_path) as f:
            data = json.load(f)
        found.add(data["name"])
        assert "embedding:register" in data["capabilities"]
        assert data["schema_version"] == "1.0.0"
    assert found == expected, f"Missing manifests: {expected - found}"
