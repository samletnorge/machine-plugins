"""Tests for sentence-transformers embedding provider plugin."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


class TestSentenceTransformersEmbeddingProvider:
    @pytest.fixture
    def provider(self):
        from embeddings_sentence_transformers import (
            EmbeddingsSentenceTransformersPlugin,
        )

        provider = EmbeddingsSentenceTransformersPlugin()
        provider._model_name = "all-MiniLM-L6-v2"
        return provider

    async def test_embed_single(self, provider):
        mock_model = MagicMock()
        mock_vectors = MagicMock()
        mock_vectors.tolist.return_value = [[0.1, 0.2, 0.3]]
        mock_model.encode.return_value = mock_vectors

        with patch.object(provider, "_get_model", return_value=mock_model):
            result = await provider.embed(EmbeddingRequest(input="hello"))

        assert isinstance(result, EmbeddingResult)
        assert result.vectors == [[0.1, 0.2, 0.3]]
        assert result.dimensions == 3
        assert result.model_ref == "all-MiniLM-L6-v2"

    async def test_embed_batch(self, provider):
        mock_model = MagicMock()
        mock_vectors = MagicMock()
        mock_vectors.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode.return_value = mock_vectors

        with patch.object(provider, "_get_model", return_value=mock_model):
            result = await provider.embed(EmbeddingRequest(input=["a", "b"]))

        assert isinstance(result, EmbeddingResult)
        assert result.vectors == [[0.1, 0.2], [0.3, 0.4]]
        assert result.dimensions == 2
        assert result.usage == {"input_count": 2}
