"""Tests for pydantic-ai wrapper LLM providers (Grok, Groq, Google, Vertex)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class TestGrokProvider:
    @pytest.fixture
    def provider(self):
        from provider_grok.provider import GrokLLMProvider

        return GrokLLMProvider(api_key="test-key", model="grok-3")

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        mock_result = MagicMock()
        mock_result.data = "Grok response"
        mock_result.usage.return_value = MagicMock(
            request_tokens=5, response_tokens=3, total_tokens=8
        )
        with patch.object(provider, "_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            request = ModelRequest(provider="grok", model="grok-3", input="Hi")
            result = await provider.generate(request)
        assert isinstance(result, ModelResponse)
        assert result.provider == "grok"
        assert result.output == "Grok response"


class TestGroqProvider:
    @pytest.fixture
    def provider(self):
        from provider_groq.provider import GroqLLMProvider

        return GroqLLMProvider(api_key="test-key", model="llama-3.3-70b-versatile")

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        mock_result = MagicMock()
        mock_result.data = "Groq response"
        mock_result.usage.return_value = MagicMock(
            request_tokens=5, response_tokens=3, total_tokens=8
        )
        with patch.object(provider, "_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            request = ModelRequest(
                provider="groq", model="llama-3.3-70b-versatile", input="Hi"
            )
            result = await provider.generate(request)
        assert isinstance(result, ModelResponse)
        assert result.provider == "groq"


class TestGoogleGeminiProvider:
    @pytest.fixture
    def provider(self):
        from provider_google_gemini.provider import (
            GoogleGeminiLLMProvider,
        )

        return GoogleGeminiLLMProvider(api_key="test-key", model="gemini-2.0-flash")

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        mock_result = MagicMock()
        mock_result.data = "Gemini response"
        mock_result.usage.return_value = MagicMock(
            request_tokens=5, response_tokens=3, total_tokens=8
        )
        with patch.object(provider, "_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            request = ModelRequest(
                provider="google-gemini", model="gemini-2.0-flash", input="Hi"
            )
            result = await provider.generate(request)
        assert isinstance(result, ModelResponse)
        assert result.provider == "google-gemini"


class TestVertexGeminiProvider:
    @pytest.fixture
    def provider(self):
        from provider_vertex_gemini.provider import (
            VertexGeminiLLMProvider,
        )

        return VertexGeminiLLMProvider(
            project="my-project", location="us-central1", model="gemini-2.0-flash"
        )

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        mock_result = MagicMock()
        mock_result.data = "Vertex Gemini response"
        mock_result.usage.return_value = MagicMock(
            request_tokens=5, response_tokens=3, total_tokens=8
        )
        with patch.object(provider, "_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            request = ModelRequest(
                provider="vertex-gemini", model="gemini-2.0-flash", input="Hi"
            )
            result = await provider.generate(request)
        assert isinstance(result, ModelResponse)
        assert result.provider == "vertex-gemini"


class TestVertexClaudeProvider:
    @pytest.fixture
    def provider(self):
        from provider_vertex_claude.provider import (
            VertexClaudeLLMProvider,
        )

        return VertexClaudeLLMProvider(
            project="my-project", location="us-east5", model="claude-sonnet-4-20250514"
        )

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        mock_result = MagicMock()
        mock_result.data = "Claude on Vertex response"
        mock_result.usage.return_value = MagicMock(
            request_tokens=5, response_tokens=3, total_tokens=8
        )
        with patch.object(provider, "_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            request = ModelRequest(
                provider="vertex-claude", model="claude-sonnet-4-20250514", input="Hi"
            )
            result = await provider.generate(request)
        assert isinstance(result, ModelResponse)
        assert result.provider == "vertex-claude"


@pytest.mark.asyncio
async def test_all_pydantic_ai_manifests_exist():
    from machine_core.plugins import builtin_manifests

    manifests = {m.name: m for m in builtin_manifests()}
    expected = [
        "provider-grok",
        "provider-groq",
        "provider-google-gemini",
        "provider-vertex-gemini",
        "provider-vertex-claude",
    ]
    for name in expected:
        assert name in manifests, f"Missing manifest for {name}"
        assert any("pydantic-ai" in d for d in manifests[name].dependencies), (
            f"{name} should depend on pydantic-ai"
        )
