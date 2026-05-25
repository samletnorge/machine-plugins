"""Docker deployer — generates Dockerfile and docker-compose.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deployer_support.base import (
    Deployer,
    DeployConfig,
    DeployResult,
    DeployStatus,
)


class DockerDeployer(Deployer):
    """Generate Dockerfile and docker-compose.yml for a machine-core project."""

    name: str = "docker"

    async def deploy(self, machine: Any, config: DeployConfig) -> DeployResult:
        output_dir = Path(config.extra.get("output_dir", "."))
        entry = config.extra.get("entry", "src.main:machine")
        module_path, _, attr_name = entry.rpartition(":")
        port = config.port

        dockerfile_content = f'''FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen || uv sync --no-dev

# Copy application code
COPY . .

EXPOSE {port}

CMD ["uv", "run", "uvicorn", "{module_path}:{attr_name}", "--host", "0.0.0.0", "--port", "{port}", "--factory"]
'''

        env_section = ""
        if config.env_vars:
            env_lines = "\n".join(f"      {k}: {v}" for k, v in config.env_vars.items())
            env_section = f"""
    environment:
{env_lines}"""

        compose_content = f'''version: "3.8"

services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    restart: unless-stopped{env_section}
'''

        (output_dir / "Dockerfile").write_text(dockerfile_content)
        (output_dir / "docker-compose.yml").write_text(compose_content)

        return DeployResult(
            status=DeployStatus.SUCCESS,
            message=f"Generated Dockerfile and docker-compose.yml in {output_dir}",
            metadata={
                "dockerfile": str(output_dir / "Dockerfile"),
                "compose": str(output_dir / "docker-compose.yml"),
            },
        )
