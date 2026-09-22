"""Deployer-support plugin.

Defines the "deployer" category and registers built-in deployers
for various deployment targets (Docker, Dokploy, Vercel, Cloudflare).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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


def _get_builtin_deployer(name: str):
    """Get a built-in deployer by name (fallback when Machine isn't available)."""
    from .docker import DockerDeployer
    from .vercel import VercelDeployer
    from .cloudflare import CloudflareDeployer

    deployers = {
        "docker": DockerDeployer,
        "vercel": VercelDeployer,
        "cloudflare": CloudflareDeployer,
    }
    cls = deployers.get(name)
    return cls() if cls else None


class DeployerSupportPlugin:
    """Plugin that provides the deployer category and built-in deployers."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

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

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
