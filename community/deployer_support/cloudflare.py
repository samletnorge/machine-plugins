"""Cloudflare Workers deployer — generate wrangler config."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from deployer_support.base import (
    Deployer,
    DeployConfig,
    DeployResult,
    DeployStatus,
)


class CloudflareDeployer(Deployer):
    """Generate Cloudflare Workers deployment configuration."""

    name: str = "cloudflare"

    async def deploy(self, machine: Any, config: DeployConfig) -> DeployResult:
        output_dir = Path(config.extra.get("output_dir", "."))
        project_name = config.extra.get("name", "machine-core-app")

        env_section = ""
        if config.env_vars:
            vars_lines = "\n".join(f'{k} = "{v}"' for k, v in config.env_vars.items())
            env_section = f"\n[vars]\n{vars_lines}\n"

        wrangler_content = f'''name = "{project_name}"
main = "src/worker.py"
compatibility_date = "{date.today().isoformat()}"
{env_section}
[build]
command = "pip install -r requirements.txt -t ./packages"
'''
        (output_dir / "wrangler.toml").write_text(wrangler_content)

        return DeployResult(
            status=DeployStatus.SUCCESS,
            message=f"Generated wrangler.toml in {output_dir}",
            metadata={"wrangler_toml": str(output_dir / "wrangler.toml")},
        )
