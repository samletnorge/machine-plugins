"""Tests for DeployerSupportPlugin and _get_builtin_deployer registration."""

import pytest

from deployer_support import (
    DeployerSupportPlugin,
    _get_builtin_deployer,
    _resolve_dokploy_credentials,
)
from deployer_support.cloudflare import CloudflareDeployer
from deployer_support.docker import DockerDeployer
from deployer_support.dokploy import DokployDeployer
from deployer_support.vercel import VercelDeployer


class _MockCtx:
    def __init__(self):
        self.categories = {}
        self.items = []

    def register_category(self, name, **kwargs):
        self.categories[name] = kwargs

    def register(self, category, name, impl):
        self.items.append((category, name, impl))


def _clear_dokploy_env(monkeypatch):
    monkeypatch.delenv("DOKPLOY_API_URL", raising=False)
    monkeypatch.delenv("DOKPLOY_API_TOKEN", raising=False)


def _registered_deployers(ctx):
    return {name for cat, name, _ in ctx.items if cat == "deployer"}


def test_builtin_docker_vercel_cloudflare_still_work(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    assert isinstance(_get_builtin_deployer("docker"), DockerDeployer)
    assert isinstance(_get_builtin_deployer("vercel"), VercelDeployer)
    assert isinstance(_get_builtin_deployer("cloudflare"), CloudflareDeployer)


def test_builtin_dokploy_returns_none_without_config_or_env(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    assert _get_builtin_deployer("dokploy") is None


def test_builtin_dokploy_from_env(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    monkeypatch.setenv("DOKPLOY_API_URL", "https://dokploy.example.com")
    monkeypatch.setenv("DOKPLOY_API_TOKEN", "env-token")

    deployer = _get_builtin_deployer("dokploy")
    assert isinstance(deployer, DokployDeployer)
    assert deployer.api_url == "https://dokploy.example.com"
    assert deployer.api_token == "env-token"


def test_builtin_dokploy_from_config(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    deployer = _get_builtin_deployer(
        "dokploy",
        {"api_url": "https://cfg.example.com", "api_token": "cfg-token"},
    )
    assert isinstance(deployer, DokployDeployer)
    assert deployer.api_url == "https://cfg.example.com"
    assert deployer.api_token == "cfg-token"


def test_resolve_dokploy_credentials_config_wins_over_env(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    monkeypatch.setenv("DOKPLOY_API_URL", "https://env.example.com")
    monkeypatch.setenv("DOKPLOY_API_TOKEN", "env-token")
    api_url, api_token = _resolve_dokploy_credentials(
        {"api_url": "https://cfg.example.com", "api_token": "cfg-token"}
    )
    assert api_url == "https://cfg.example.com"
    assert api_token == "cfg-token"


@pytest.mark.asyncio
async def test_setup_registers_dokploy_with_config(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    plugin = DeployerSupportPlugin()
    await plugin.initialize(
        config={"api_url": "https://dokploy.example.com", "api_token": "tok"}
    )
    ctx = _MockCtx()
    await plugin.setup(ctx)

    assert "deployer" in ctx.categories
    assert {"docker", "vercel", "cloudflare", "dokploy"} <= _registered_deployers(ctx)


@pytest.mark.asyncio
async def test_setup_skips_dokploy_without_credentials(monkeypatch):
    _clear_dokploy_env(monkeypatch)
    plugin = DeployerSupportPlugin()
    await plugin.initialize(config={})
    ctx = _MockCtx()
    await plugin.setup(ctx)

    names = _registered_deployers(ctx)
    assert {"docker", "vercel", "cloudflare"} <= names
    assert "dokploy" not in names
