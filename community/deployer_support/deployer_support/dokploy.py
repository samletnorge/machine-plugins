"""Dokploy deployer — deploy to Dokploy via API."""

from __future__ import annotations

from typing import Any

import httpx

from deployer_support.base import (
    Deployer,
    DeployConfig,
    DeployResult,
    DeployStatus,
)


class DokployDeployer(Deployer):
    """Deploy a machine-core project to Dokploy."""

    name: str = "dokploy"
    api_url: str
    api_token: str

    async def deploy(self, machine: Any, config: DeployConfig) -> DeployResult:
        application_id = config.extra.get("application_id")
        if not application_id:
            return DeployResult(
                status=DeployStatus.FAILED,
                message="Missing application_id in config.extra",
                error="application_id is required for Dokploy deployment",
            )

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.api_url, headers=headers
            ) as client:
                if config.env_vars:
                    env_str = "\n".join(f"{k}={v}" for k, v in config.env_vars.items())
                    await client.post(
                        "/api/application.saveEnvironment",
                        json={
                            "applicationId": application_id,
                            "env": env_str,
                            "buildArgs": None,
                            "buildSecrets": None,
                            "createEnvFile": True,
                        },
                    )

                resp = await client.post(
                    "/api/application.deploy",
                    json={
                        "applicationId": application_id,
                    },
                )

                if resp.status_code == 200:
                    return DeployResult(
                        status=DeployStatus.SUCCESS,
                        message=f"Deployment triggered for {application_id}",
                        deploy_id=application_id,
                        metadata={"response": resp.json()},
                    )
                else:
                    return DeployResult(
                        status=DeployStatus.FAILED,
                        message=f"Dokploy API returned {resp.status_code}",
                        error=resp.text,
                    )
        except Exception as e:
            return DeployResult(
                status=DeployStatus.FAILED,
                message="Dokploy deployment failed",
                error=str(e),
            )

    async def teardown(self, deploy_id: str) -> None:
        headers = {"Authorization": f"Bearer {self.api_token}"}
        async with httpx.AsyncClient(base_url=self.api_url, headers=headers) as client:
            await client.post(
                "/api/application.stop",
                json={
                    "applicationId": deploy_id,
                },
            )
