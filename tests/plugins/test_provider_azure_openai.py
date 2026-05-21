"""Tests for provider-azure-openai LLM plugin."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from machine_core import Machine
from machine_core.plugin.manifest import PluginManifest
from machine_core.plugins.model_provider_support.schemas import (
    ModelProviderConfig,
    ModelRequest,
    ModelResponse,
)


async def test_azure_manifest_has_dependencies():
    from machine_core.plugins import builtin_manifests

    manifests = builtin_manifests()
    azure = next((m for m in manifests if m.name == "provider-azure-openai"), None)
    assert azure is not None
    assert any("pydantic-ai" in d for d in azure.dependencies)


class TestAzureOpenAIProvider:
    @pytest.fixture
    def provider(self):
        from machine_core.plugins.provider_azure_openai.provider import (
            AzureOpenAILLMProvider,
        )

        return AzureOpenAILLMProvider(
            endpoint="https://myresource.openai.azure.com",
            api_key="test-key",
            deployment="gpt-4o",
            api_version="2024-12-01-preview",
        )

    async def test_generate_returns_model_response(self, provider):
        mock_result = MagicMock()
        mock_result.data = "Azure says hello"
        mock_result.usage.return_value = MagicMock(
            request_tokens=10, response_tokens=5, total_tokens=15
        )

        with patch.object(provider, "_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)

            request = ModelRequest(
                provider="azure-openai", model="gpt-4o", input="Hello"
            )
            result = await provider.generate(request)

        assert isinstance(result, ModelResponse)
        assert result.provider == "azure-openai"
        assert result.output == "Azure says hello"

    async def test_generate_with_token_auth(self):
        from machine_core.plugins.provider_azure_openai.provider import (
            AzureOpenAILLMProvider,
        )

        provider = AzureOpenAILLMProvider(
            endpoint="https://myresource.openai.azure.com",
            api_key="test-key",
            deployment="gpt-4o",
            api_version="2024-12-01-preview",
            use_token_auth=False,
        )
        assert provider is not None
