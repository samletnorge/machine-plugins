"""Tests for Deployer ABC and models."""

import pytest
from deployer_support.base import (
    Deployer,
    DeployConfig,
    DeployResult,
    DeployStatus,
)


def test_deploy_config_defaults():
    """DeployConfig has sensible defaults."""
    config = DeployConfig(target="docker")
    assert config.target == "docker"
    assert config.env_vars == {}
    assert config.port == 8000


def test_deploy_config_custom():
    """DeployConfig accepts custom values."""
    config = DeployConfig(
        target="dokploy",
        env_vars={"API_KEY": "secret"},
        port=9000,
        region="eu-west-1",
    )
    assert config.env_vars == {"API_KEY": "secret"}
    assert config.port == 9000
    assert config.region == "eu-west-1"


def test_deploy_result_success():
    """DeployResult models a successful deployment."""
    result = DeployResult(
        status=DeployStatus.SUCCESS,
        url="https://app.example.com",
        message="Deployed successfully",
    )
    assert result.status == DeployStatus.SUCCESS
    assert result.url == "https://app.example.com"


def test_deploy_result_failure():
    """DeployResult models a failed deployment."""
    result = DeployResult(
        status=DeployStatus.FAILED,
        message="Build failed",
        error="Exit code 1",
    )
    assert result.status == DeployStatus.FAILED
    assert result.error == "Exit code 1"


def test_deployer_is_abstract():
    """Cannot instantiate Deployer directly."""
    with pytest.raises(TypeError):
        Deployer()


class DummyDeployer(Deployer):
    name: str = "dummy"

    async def deploy(self, machine, config: DeployConfig) -> DeployResult:
        return DeployResult(status=DeployStatus.SUCCESS, message="ok")

    async def teardown(self, deploy_id: str) -> None:
        pass


@pytest.mark.asyncio
async def test_dummy_deployer():
    """Concrete deployer works."""
    deployer = DummyDeployer()
    result = await deployer.deploy(None, DeployConfig(target="dummy"))
    assert result.status == DeployStatus.SUCCESS
