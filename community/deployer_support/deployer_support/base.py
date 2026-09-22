"""Deployer ABC and shared models.

All deployers implement the Deployer interface and return DeployResult.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeployStatus(str, Enum):
    """Deployment status."""

    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"


class DeployConfig(BaseModel):
    """Configuration for a deployment."""

    target: str = Field(
        ..., description="Deployment target (docker, dokploy, vercel, cloudflare)"
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict, description="Environment variables to set"
    )
    port: int = Field(default=8008, description="Port to expose")
    region: str | None = Field(default=None, description="Deployment region")
    replicas: int = Field(default=1, description="Number of replicas")
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific config"
    )


class DeployResult(BaseModel):
    """Result of a deployment operation."""

    status: DeployStatus
    url: str | None = None
    message: str | None = None
    error: str | None = None
    deploy_id: str | None = None
    logs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Deployer(BaseModel, ABC):
    """Abstract base class for deployers.

    Subclass and implement deploy() and optionally teardown().
    """

    name: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    async def deploy(self, machine: Any, config: DeployConfig) -> DeployResult:
        """Deploy the machine-core project."""
        ...

    async def teardown(self, deploy_id: str) -> None:
        """Tear down a previous deployment. Optional."""
        pass
