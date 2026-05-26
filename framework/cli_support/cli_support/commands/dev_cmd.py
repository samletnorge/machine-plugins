"""machine dev — start development server with hot reload."""

from __future__ import annotations

import os
import subprocess
import sys

import typer
from rich.console import Console

from cli_support.manifest_sync import sync_manifests
from cli_support.utils import (
    find_project_root,
    load_machine_config,
)

console = Console()


def dev_command(
    port: int = typer.Option(
        8000, "--port", "-p", help="Port to run the dev server on."
    ),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to."),
):
    """Start development server with hot reload."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    # Sync plugin manifests from site-packages to ~/.config/machine-core/plugins/
    console.print("[dim]Syncing plugin manifests...[/dim]")
    sync_manifests(project_root=root)

    console.print(f"[green]Starting dev server...[/green]")
    console.print(f"  URL: http://{host}:{port}")
    console.print(f"  Entry: {entry}")

    # Ensure server_support is installed (required for machine dev)
    try:
        import server_support  # noqa: F401
    except ImportError:
        console.print("[yellow]Installing server-support plugin...[/yellow]")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/server_support",
            ],
            check=True,
            capture_output=True,
        )

    # Ensure agent_support is installed
    try:
        import agent_support  # noqa: F401
    except ImportError:
        console.print("[yellow]Installing agent_support plugin...[/yellow]")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/agent_support",
            ],
            check=True,
            capture_output=True,
        )

    # Ensure tool_support is installed
    try:
        import tool_support  # noqa: F401
    except ImportError:
        console.print("[yellow]Installing tool_support plugin...[/yellow]")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/tool_support",
            ],
            check=True,
            capture_output=True,
        )

    env_vars = {
        "MACHINE_CORE_ENTRY": entry,
        "MACHINE_CORE_ROOT": str(root),
    }

    # Use the project's venv Python so all project plugins are importable
    venv_python = root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        console.print("[red]Error: No .venv found. Run 'uv sync' first.[/red]")
        raise typer.Exit(code=1)

    # Write a dev server bootstrap script into the project so it's importable
    # from the project's venv (which doesn't have cli_support installed)
    dev_server_code = f'''\
"""Auto-generated dev server for machine dev. Do not edit."""
import os, sys
sys.path.insert(0, os.environ.get("MACHINE_CORE_ROOT", "."))
import importlib
module = importlib.import_module("{entry.rpartition(":")[0]}")
machine = getattr(module, "{entry.rpartition(":")[2]}")
from server_support.app import create_app
app = create_app(machine)
'''
    dev_server_file = root / "_machine_dev_server.py"
    dev_server_file.write_text(dev_server_code)

    cmd = [
        str(venv_python),
        "-m",
        "uvicorn",
        "_machine_dev_server:app",
        "--reload",
        "--host",
        host,
        "--port",
        str(port),
    ]

    # Only add --reload-dir if src/ exists
    src_dir = root / "src"
    if src_dir.is_dir():
        cmd.extend(["--reload-dir", str(src_dir)])

    full_env = {**os.environ, **env_vars}
    try:
        subprocess.run(cmd, cwd=str(root), env=full_env)
    finally:
        # Clean up generated dev server file
        dev_server_file.unlink(missing_ok=True)
