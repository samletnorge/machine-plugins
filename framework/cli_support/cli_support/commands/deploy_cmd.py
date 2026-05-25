"""machine deploy — deploy to target platform via deployer plugins."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from cli_support.utils import (
    find_project_root,
    load_machine_config,
    load_machine_instance,
)

try:
    from machine_core.plugins.deployer_support.base import DeployConfig
except ImportError:
    DeployConfig = None  # type: ignore[assignment, misc]

console = Console()


def deploy_command(
    target: str = typer.Option(
        ...,
        "--target",
        "-t",
        help="Deployment target (docker, dokploy, vercel, cloudflare).",
    ),
    port: int = typer.Option(8000, "--port", "-p", help="Port to expose."),
    env: list[str] = typer.Option(
        [], "--env", "-e", help="Environment variables (KEY=VALUE)."
    ),
):
    """Deploy to target platform."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    env_vars = {}
    for e_item in env:
        if "=" in e_item:
            k, _, v = e_item.partition("=")
            env_vars[k] = v

    config_data = load_machine_config(root)
    entry = config_data.get("entry", "src.main:machine")

    deploy_config = DeployConfig(
        target=target,
        port=port,
        env_vars=env_vars,
        extra={"output_dir": str(root), "entry": entry},
    )

    # Try to resolve deployer from Machine registry first
    deployer = None
    try:
        machine = load_machine_instance(root)
        deployer = machine.resolve("deployer", target)
    except (SystemExit, Exception):
        pass

    if deployer is None:
        # Fallback: import deployer directly
        from machine_core.plugins.deployer_support import _get_builtin_deployer

        deployer = _get_builtin_deployer(target)

    if deployer is None:
        console.print(
            f"[red]Unknown target: {target}. Available: docker, dokploy, vercel, cloudflare[/red]"
        )
        raise typer.Exit(code=1)

    console.print(f"[bold]Deploying to {target}...[/bold]")

    result = asyncio.run(deployer.deploy(None, deploy_config))

    if result.status.value == "success":
        console.print(f"[green]✓[/green] {result.message}")
        if result.url:
            console.print(f"  URL: {result.url}")
    else:
        console.print(f"[red]✗[/red] {result.message}")
        if result.error:
            console.print(f"  Error: {result.error}")
        raise typer.Exit(code=1)
