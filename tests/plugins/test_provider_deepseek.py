"""Tests for the DeepSeek model provider (mocked httpx)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from model_provider_support.schemas import ModelRequest


@pytest.fixture
def provider():
    from provider_deepseek.provider import DeepSeekLLMProvider

    return DeepSeekLLMProvider(
        base_url="https://api.deepseek.com",
        api_key="test-key",
        model="deepseek-chat",
    )


def _client_returning(payload, *, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


async def test_generate_parses_openai_shape(provider):
    payload = {
        "model": "deepseek-chat",
        "choices": [{"message": {"role": "assistant", "content": "hello"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 5},
    }
    with patch(
        "provider_deepseek.provider.httpx.AsyncClient",
        return_value=_client_returning(payload),
    ):
        result = await provider.generate(ModelRequest(provider="deepseek", model="deepseek-chat", input="hi"))

    assert result.provider == "deepseek"
    assert result.output == "hello"
    assert result.usage["completion_tokens"] == 5


async def test_generate_passes_api_key_header(provider):
    payload = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
    client = _client_returning(payload)
    with patch("provider_deepseek.provider.httpx.AsyncClient", return_value=client):
        await provider.generate(ModelRequest(provider="deepseek", model="deepseek-chat", input="hi"))

    _, kwargs = client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


async def test_plugin_skips_registration_without_key():
    from provider_deepseek import DeepSeekProviderPlugin

    plugin = DeepSeekProviderPlugin()
    await plugin.initialize(config={"api_key": ""})

    registered = []
    ctx = MagicMock()
    ctx.register = lambda *args: registered.append(args)

    await plugin.setup(ctx)

    assert registered == []


async def test_plugin_registers_with_key():
    from provider_deepseek import DeepSeekProviderPlugin

    plugin = DeepSeekProviderPlugin()
    await plugin.initialize(config={"api_key": "k"})

    registered = []
    ctx = MagicMock()
    ctx.register = lambda *args: registered.append(args)

    await plugin.setup(ctx)

    assert registered and registered[0][0] == "model_provider"
    assert registered[0][1] == "deepseek"
