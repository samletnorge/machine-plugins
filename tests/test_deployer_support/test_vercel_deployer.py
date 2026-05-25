"""Tests for Vercel deployer."""

import pytest
import json
from deployer_support.vercel import VercelDeployer
from deployer_support.base import DeployConfig, DeployStatus


@pytest.fixture
def vercel_deployer():
    return VercelDeployer()


def test_vercel_deployer_name(vercel_deployer):
    assert vercel_deployer.name == "vercel"


@pytest.mark.asyncio
async def test_vercel_generates_config(vercel_deployer, tmp_path):
    """VercelDeployer generates vercel.json."""
    config = DeployConfig(
        target="vercel",
        extra={"output_dir": str(tmp_path), "entry": "src.main:machine"},
    )
    result = await vercel_deployer.deploy(None, config)

    vercel_json = tmp_path / "vercel.json"
    assert vercel_json.exists()
    data = json.loads(vercel_json.read_text())
    assert "builds" in data or "functions" in data


@pytest.mark.asyncio
async def test_vercel_generates_api_handler(vercel_deployer, tmp_path):
    """VercelDeployer generates api/index.py handler."""
    config = DeployConfig(
        target="vercel",
        extra={"output_dir": str(tmp_path), "entry": "src.main:machine"},
    )
    await vercel_deployer.deploy(None, config)

    handler = tmp_path / "api" / "index.py"
    assert handler.exists()
    content = handler.read_text()
    assert "handler" in content.lower() or "app" in content
