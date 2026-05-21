"""Tests for provider-ollama LLM plugin."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from machine_core import Machine
from machine_core.plugin.manifest import PluginManifest
from machine_core.plugins.model_provider_support.schemas import (
    ModelProviderConfig,
    ModelRequest,
    ModelResponse,
)


# --- Registration Tests ---


async def test_ollama_registers_as_model_provider():
    """Ollama plugin should register into the model_provider category."""
    m = Machine()
    await m.start()
    providers = m.list_category("model_provider")
    if "ollama" in providers:
        assert providers["ollama"] is not None
    await m.shutdown()


async def test_ollama_manifest_has_dependencies():
    """Ollama manifest should declare its dependencies."""
    from machine_core.plugins import builtin_manifests

    manifests = builtin_manifests()
    ollama = next((m for m in manifests if m.name == "provider-ollama"), None)
    assert ollama is not None
    assert "httpx" in " ".join(ollama.dependencies).lower()


# --- Provider Unit Tests (mocked httpx) ---


class TestOllamaProviderGenerate:
    @pytest.fixture
    def provider(self):
        from machine_core.plugins.provider_ollama.provider import OllamaLLMProvider

        return OllamaLLMProvider(
            base_url="http://localhost:11434",
            model="llama3.2",
        )

    @pytest.fixture
    def mock_response(self):
        return {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "Hello! How can I help?"},
            "prompt_eval_count": 10,
            "eval_count": 8,
            "total_duration": 500000000,
        }

    async def test_generate_returns_model_response(self, provider, mock_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            request = ModelRequest(
                provider="ollama",
                model="llama3.2",
                input="Hello",
            )
            result = await provider.generate(request)

        assert isinstance(result, ModelResponse)
        assert result.provider == "ollama"
        assert result.output == "Hello! How can I help?"
        assert result.usage["prompt_tokens"] == 10
        assert result.usage["completion_tokens"] == 8
        assert result.duration_ms is not None

    async def test_generate_with_message_list(self, provider, mock_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            request = ModelRequest(
                provider="ollama",
                model="llama3.2",
                input=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"},
                ],
            )
            result = await provider.generate(request)

        assert result.output == "Hello! How can I help?"
        call_args = client_instance.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert len(payload["messages"]) == 2

    async def test_generate_http_error_raises(self, provider):
        import httpx

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
        )

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_resp
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            request = ModelRequest(provider="ollama", model="llama3.2", input="Hello")

            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate(request)


class TestOllamaProviderStream:
    @pytest.fixture
    def provider(self):
        from machine_core.plugins.provider_ollama.provider import OllamaLLMProvider

        return OllamaLLMProvider(base_url="http://localhost:11434", model="llama3.2")

    async def test_stream_yields_chunks(self, provider):
        chunks = [
            json.dumps({"message": {"content": "Hello"}, "done": False}),
            json.dumps({"message": {"content": " world"}, "done": False}),
            json.dumps({"message": {"content": "!"}, "done": True}),
        ]

        async def mock_aiter_lines():
            for chunk in chunks:
                yield chunk

        mock_stream_resp = AsyncMock()
        mock_stream_resp.raise_for_status = MagicMock()
        mock_stream_resp.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = MagicMock()
            stream_ctx = AsyncMock()
            stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_resp)
            stream_ctx.__aexit__ = AsyncMock(return_value=False)
            client_instance.stream.return_value = stream_ctx
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            request = ModelRequest(
                provider="ollama", model="llama3.2", input="Hello", stream=True
            )
            collected = []
            async for chunk in provider.stream(request):
                collected.append(chunk)

        assert collected == ["Hello", " world", "!"]


class TestOllamaProviderPydanticModel:
    def test_get_pydantic_model(self):
        """Ollama provider exposes a pydantic-ai model."""
        from machine_core.plugins.provider_ollama.provider import OllamaLLMProvider

        provider = OllamaLLMProvider(
            base_url="http://localhost:9012", model="gemma4:latest"
        )
        model = provider.get_pydantic_model()
        assert model is not None
        assert hasattr(model, "model_name")


class TestOllamaProviderProtocol:
    def test_implements_provider_protocol(self):
        from machine_core.plugins.provider_ollama.provider import OllamaLLMProvider
        from machine_core.types import Provider

        provider = OllamaLLMProvider(
            base_url="http://localhost:11434", model="llama3.2"
        )
        assert isinstance(provider, Provider)
