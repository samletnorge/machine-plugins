"""Deployer-support plugin.

Defines the "deployer" category and registers built-in deployers
for various deployment targets (Docker, Dokploy, Vercel, Cloudflare).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

from .base import Deployer, DeployConfig, DeployResult, DeployStatus

__all__ = [
    "Deployer",
    "DeployConfig",
    "DeployResult",
    "DeployStatus",
    "DeployerSupportPlugin",
]


def _resolve_dokploy_credentials(config: dict | None = None) -> tuple[str | None, str | None]:
    """Resolve Dokploy credentials from plugin config or environment."""
    config = config or {}
    api_url = config.get("api_url") or config.get("dokploy_api_url")
    api_token = config.get("api_token") or config.get("dokploy_api_token")
    if not api_url:
        api_url = os.environ.get("DOKPLOY_API_URL")
    if not api_token:
        api_token = os.environ.get("DOKPLOY_API_TOKEN")
    return api_url, api_token


def _get_builtin_deployer(name: str, config: dict | None = None):
    """Get a built-in deployer by name (fallback when Machine isn't available)."""
    from .docker import DockerDeployer
    from .vercel import VercelDeployer
    from .cloudflare import CloudflareDeployer

    if name == "docker":
        return DockerDeployer()
    if name == "vercel":
        return VercelDeployer()
    if name == "cloudflare":
        return CloudflareDeployer()
    if name == "dokploy":
        api_url, api_token = _resolve_dokploy_credentials(config)
        if not (api_url and api_token):
            return None
        from .dokploy import DokployDeployer

        return DokployDeployer(api_url=api_url, api_token=api_token)
    return None


class DeployerSupportPlugin:
    """Plugin that provides the deployer category and built-in deployers."""

    def __init__(self) -> None:
        self._config: dict = {}

    async def initialize(self, config=None, **kwargs):
        self._config = config or {}

    async def setup(self, ctx: "PluginContext"):
        """Register the deployer category and all built-in deployers."""
        from .docker import DockerDeployer
        from .vercel import VercelDeployer
        from .cloudflare import CloudflareDeployer

        ctx.register_category(
            "deployer",
            operations={
                "deploy": {"method": "POST", "on": "item"},
                "teardown": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )

        ctx.register("deployer", "docker", DockerDeployer())
        ctx.register("deployer", "vercel", VercelDeployer())
        ctx.register("deployer", "cloudflare", CloudflareDeployer())

        dokploy = _get_builtin_deployer("dokploy", self._config)
        if dokploy is not None:
            ctx.register("deployer", "dokploy", dokploy)
        else:
            logger.debug(
                "deployer_support: skipping 'dokploy' — set api_url/api_token "
                "in plugin config or DOKPLOY_API_URL/DOKPLOY_API_TOKEN"
            )

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
