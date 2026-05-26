"""Tests for provider_github_copilot LLM plugin."""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class TestCopilotAuth:
    async def test_copilot_token_exchange(self):
        from provider_github_copilot.auth import CopilotAuth

        auth = CopilotAuth(access_token="gho_test_oauth_token")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "token": "tid=copilot-session-token",
            "expires_at": int(time.time()) + 3600,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            client.get.return_value = mock_resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            await auth._refresh()

        assert auth._copilot_token == "tid=copilot-session-token"
        assert not auth.is_expired

    async def test_token_cached_when_valid(self):
        from provider_github_copilot.auth import CopilotAuth

        auth = CopilotAuth(access_token="gho_test")
        auth._copilot_token = "cached-token"
        auth._expires_at = time.time() + 3600

        assert not auth.is_expired

    async def test_token_expired_with_buffer(self):
        from provider_github_copilot.auth import CopilotAuth

        auth = CopilotAuth(access_token="gho_test")
        auth._copilot_token = "old-token"
        # Expires in 4 minutes — within 5 min buffer, so should be "expired"
        auth._expires_at = time.time() + 240

        assert auth.is_expired

    async def test_base_url(self):
        from provider_github_copilot.auth import CopilotAuth

        auth = CopilotAuth(access_token="gho_test")
        assert auth.base_url == "https://api.githubcopilot.com"

    async def test_device_flow_login(self):
        from provider_github_copilot.auth import device_flow_login

        mock_device_resp = MagicMock()
        mock_device_resp.json.return_value = {
            "device_code": "dc_test",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "interval": 1,
            "expires_in": 900,
        }
        mock_device_resp.raise_for_status = MagicMock()

        mock_poll_resp = MagicMock()
        mock_poll_resp.json.return_value = {"access_token": "gho_new_token"}

        with (
            patch("httpx.AsyncClient") as MockClient,
            patch("webbrowser.open_new_tab"),
            patch("provider_github_copilot.auth.CONFIG_DIR") as mock_dir,
            patch("provider_github_copilot.auth.TOKEN_FILE") as mock_file,
        ):
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[mock_device_resp, mock_poll_resp])
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            token = await device_flow_login()

        assert token == "gho_new_token"

    def test_copilot_headers_have_required_fields(self):
        from provider_github_copilot.auth import copilot_headers

        headers = copilot_headers()
        assert "copilot-integration-id" in headers
        assert headers["copilot-integration-id"] == "vscode-chat"
        assert "x-request-id" in headers
        assert "x-github-api-version" in headers

    def test_github_headers_have_required_fields(self):
        from provider_github_copilot.auth import github_headers

        headers = github_headers()
        assert "editor-version" in headers
        assert "user-agent" in headers
        assert "x-github-api-version" in headers


class TestCopilotProvider:
    @pytest.fixture
    def provider(self):
        from provider_github_copilot.provider import (
            CopilotLLMProvider,
        )

        return CopilotLLMProvider.__new__(CopilotLLMProvider)

    async def test_generate(self, provider):
        mock_result = MagicMock()
        mock_result.output = "Copilot says hello"
        mock_result.data = "Copilot says hello"  # fallback compat
        mock_result.usage = MagicMock(
            request_tokens=10, response_tokens=5, total_tokens=15
        )

        provider._agent = MagicMock()
        provider._agent.run = AsyncMock(return_value=mock_result)
        provider._provider_name = "github-copilot"
        provider._model_name = "gpt-4o"

        request = ModelRequest(provider="github-copilot", model="gpt-4o", input="Hello")
        result = await provider.generate(request)

        assert isinstance(result, ModelResponse)
        assert result.provider == "github-copilot"
        assert result.output == "Copilot says hello"


def test_get_pydantic_model():
    """Copilot provider exposes its pydantic-ai model."""
    from provider_github_copilot.provider import CopilotLLMProvider
    from provider_github_copilot.auth import CopilotAuth

    mock_auth = MagicMock(spec=CopilotAuth)
    mock_auth.auth_flow = MagicMock(return_value=iter([]))

    provider = CopilotLLMProvider(auth=mock_auth, model="gpt-4o")
    model = provider.get_pydantic_model()
    assert model is not None
    assert hasattr(model, "model_name")


async def test_copilot_manifest():
    from machine_core.plugins import builtin_manifests

    manifests = {m.name: m for m in builtin_manifests()}
    assert "provider_github_copilot" in manifests
    m = manifests["provider_github_copilot"]
    assert any("httpx" in d for d in m.dependencies)
