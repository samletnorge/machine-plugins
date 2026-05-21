"""provider-github-copilot: GitHub Copilot via OAuth device flow + pydantic-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class CopilotProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._access_token = config.get("access_token", "")
        self._model = config.get("model", "gpt-4o")

    async def setup(self, ctx: PluginContext):
        import httpx  # ImportError → lazy skip

        from .auth import CopilotAuth, get_cached_access_token
        from .provider import CopilotLLMProvider

        access_token = self._access_token

        # Fallback: check cached token from device flow (persisted state backup)
        if not access_token:
            access_token = get_cached_access_token()

        if not access_token:
            from loguru import logger

            logger.debug(
                "GitHub Copilot: no access token found. "
                "Run `machine-core copilot-login` or set GITHUB_COPILOT_TOKEN env var. "
                "Token is cached at ~/.config/machine-core/github-copilot/access_token"
            )
            return

        auth = CopilotAuth(access_token=access_token)
        provider = CopilotLLMProvider(auth=auth, model=self._model)
        ctx.register("model_provider", "github-copilot", provider)

    async def shutdown(self, **kwargs):
        pass
