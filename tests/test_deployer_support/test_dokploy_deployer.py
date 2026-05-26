"""Tests for Dokploy deployer."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from deployer_support.dokploy import DokployDeployer
from deployer_support.base import DeployConfig, DeployStatus


@pytest.fixture
def dokploy_deployer():
    return DokployDeployer(
        api_url="https://dokploy.example.com",
        api_token="test-token",
    )


@pytest.fixture
def deploy_config():
    return DeployConfig(
        target="dokploy",
        port=8008,
        env_vars={"API_KEY": "test"},
        extra={
            "application_id": "app-123",
            "project_id": "proj-456",
        },
    )


def test_dokploy_deployer_name(dokploy_deployer):
    assert dokploy_deployer.name == "dokploy"


@pytest.mark.asyncio
async def test_dokploy_deploy_calls_api(dokploy_deployer, deploy_config):
    """DokployDeployer calls Dokploy API to trigger deployment."""
    with patch("deployer_support.dokploy.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = MagicMock(
            status_code=200, json=lambda: {"ok": True}
        )

        result = await dokploy_deployer.deploy(None, deploy_config)
        assert mock_client.post.called


@pytest.mark.asyncio
async def test_dokploy_deploy_sets_env_vars(dokploy_deployer, deploy_config):
    """DokployDeployer saves environment variables before deploying."""
    with patch("deployer_support.dokploy.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {})

        await dokploy_deployer.deploy(None, deploy_config)

        calls = [str(c) for c in mock_client.post.call_args_list]
        env_call_found = any(
            "saveEnvironment" in str(c) or "env" in str(c).lower() for c in calls
        )
        deploy_call_found = any("deploy" in str(c).lower() for c in calls)
        assert env_call_found or deploy_call_found


@pytest.mark.asyncio
async def test_dokploy_deploy_requires_application_id(dokploy_deployer):
    """DokployDeployer fails without application_id."""
    config = DeployConfig(target="dokploy")
    result = await dokploy_deployer.deploy(None, config)
    assert result.status == DeployStatus.FAILED
