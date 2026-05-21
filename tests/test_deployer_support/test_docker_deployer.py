"""Tests for Docker deployer."""

import pytest
from machine_core.plugins.deployer_support.docker import DockerDeployer
from machine_core.plugins.deployer_support.base import DeployConfig, DeployStatus


@pytest.fixture
def docker_deployer():
    return DockerDeployer()


@pytest.fixture
def deploy_config():
    return DeployConfig(target="docker", port=8000, env_vars={"API_KEY": "test"})


def test_docker_deployer_name(docker_deployer):
    assert docker_deployer.name == "docker"


@pytest.mark.asyncio
async def test_generate_dockerfile(docker_deployer, deploy_config, tmp_path):
    """DockerDeployer generates a valid Dockerfile."""
    deploy_config.extra["output_dir"] = str(tmp_path)
    deploy_config.extra["entry"] = "src.main:machine"
    result = await docker_deployer.deploy(None, deploy_config)

    dockerfile = tmp_path / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text()
    assert "FROM python" in content
    assert "uvicorn" in content
    assert "8000" in content


@pytest.mark.asyncio
async def test_generate_docker_compose(docker_deployer, deploy_config, tmp_path):
    """DockerDeployer generates docker-compose.yml."""
    deploy_config.extra["output_dir"] = str(tmp_path)
    deploy_config.extra["entry"] = "src.main:machine"
    await docker_deployer.deploy(None, deploy_config)

    compose = tmp_path / "docker-compose.yml"
    assert compose.exists()
    content = compose.read_text()
    assert "services" in content
    assert "8000" in content


@pytest.mark.asyncio
async def test_docker_env_vars_in_compose(docker_deployer, deploy_config, tmp_path):
    """Environment variables appear in docker-compose.yml."""
    deploy_config.extra["output_dir"] = str(tmp_path)
    deploy_config.extra["entry"] = "src.main:machine"
    await docker_deployer.deploy(None, deploy_config)

    content = (tmp_path / "docker-compose.yml").read_text()
    assert "API_KEY" in content


@pytest.mark.asyncio
async def test_docker_deploy_result(docker_deployer, deploy_config, tmp_path):
    """Deploy returns success with generated file paths."""
    deploy_config.extra["output_dir"] = str(tmp_path)
    deploy_config.extra["entry"] = "src.main:machine"
    result = await docker_deployer.deploy(None, deploy_config)
    assert result.status == DeployStatus.SUCCESS
    assert "Dockerfile" in result.message or "generated" in result.message.lower()
