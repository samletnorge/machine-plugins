"""Tests for Cloudflare deployer."""

import pytest
from deployer_support.cloudflare import CloudflareDeployer
from deployer_support.base import DeployConfig, DeployStatus


@pytest.fixture
def cf_deployer():
    return CloudflareDeployer()


def test_cf_deployer_name(cf_deployer):
    assert cf_deployer.name == "cloudflare"


@pytest.mark.asyncio
async def test_cf_generates_wrangler_toml(cf_deployer, tmp_path):
    """CloudflareDeployer generates wrangler.toml."""
    config = DeployConfig(
        target="cloudflare",
        extra={"output_dir": str(tmp_path), "entry": "src.main:machine"},
    )
    result = await cf_deployer.deploy(None, config)

    wrangler = tmp_path / "wrangler.toml"
    assert wrangler.exists()
    content = wrangler.read_text()
    assert "name" in content
    assert "compatibility_date" in content
