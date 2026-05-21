"""Vercel deployer — generate serverless function config."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from machine_core.plugins.deployer_support.base import (
    Deployer,
    DeployConfig,
    DeployResult,
    DeployStatus,
)


class VercelDeployer(Deployer):
    """Generate Vercel deployment configuration."""

    name: str = "vercel"

    async def deploy(self, machine: Any, config: DeployConfig) -> DeployResult:
        output_dir = Path(config.extra.get("output_dir", "."))
        entry = config.extra.get("entry", "src.main:machine")

        vercel_config = {
            "version": 2,
            "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
            "routes": [{"src": "/(.*)", "dest": "api/index.py"}],
        }
        (output_dir / "vercel.json").write_text(json.dumps(vercel_config, indent=2))

        api_dir = output_dir / "api"
        api_dir.mkdir(exist_ok=True)

        module_path, _, attr_name = entry.rpartition(":")
        handler_content = f'''"""Vercel serverless handler for machine-core."""
from machine_core.plugins.server_support.app import create_app
from {module_path} import {attr_name}

app = create_app({attr_name})
handler = app
'''
        (api_dir / "index.py").write_text(handler_content)

        return DeployResult(
            status=DeployStatus.SUCCESS,
            message=f"Generated Vercel config in {output_dir}",
            metadata={"vercel_json": str(output_dir / "vercel.json")},
        )
