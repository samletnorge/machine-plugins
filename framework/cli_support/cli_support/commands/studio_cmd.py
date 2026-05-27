"""machine studio — launch the Studio web UI."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from cli_support.manifest_sync import sync_manifests
from cli_support.utils import (
    find_project_root,
    load_machine_config,
)

console = Console()


def _resolve_studio_source_path(installed_module_file: str) -> Path:
    pythonpath = os.environ.get("PYTHONPATH", "")
    for entry in pythonpath.split(os.pathsep):
        if not entry:
            continue
        candidate = (
            Path(entry).expanduser().resolve() / "studio_support" / "__init__.py"
        )
        if candidate.exists():
            return candidate.parent.parent
    return Path(installed_module_file).resolve().parent.parent


def studio_command(
    port: int = typer.Option(3177, "--port", "-p", help="Port to run the Studio on."),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to."),
):
    """Launch the Studio web UI for testing agents and tools."""
    import studio_support

    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    console.print("[dim]Syncing plugin manifests...[/dim]")
    sync_manifests(project_root=root)

    venv_python = root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        console.print("[red]Error: No .venv found. Run 'uv sync' first.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Starting Machine Studio...[/green]")
    console.print(f"  URL: http://{host}:{port}/_studio/")
    console.print(f"  Entry: {entry}")

    env_vars = {
        "MACHINE_CORE_ENTRY": entry,
        "MACHINE_CORE_ROOT": str(root),
        "MACHINE_STUDIO_ENABLED": "1",
    }
    studio_site_packages = _resolve_studio_source_path(studio_support.__file__)

    studio_server_code = f'''\
"""Auto-generated studio server for machine studio. Do not edit."""
import os, sys
sys.path.insert(0, os.environ.get("MACHINE_CORE_ROOT", "."))
sys.path.insert(0, {str(studio_site_packages)!r})
import importlib
module = importlib.import_module("{entry.rpartition(":")[0]}")
machine = getattr(module, "{entry.rpartition(":")[2]}")
from server_support.app import create_app
app = create_app(machine)
from studio_support.app import create_studio_app
studio = create_studio_app(machine)
app.mount("/_studio", studio)
'''
    studio_server_file = root / "_machine_studio_server.py"
    studio_server_file.write_text(studio_server_code)

    cmd = [
        str(venv_python),
        "-m",
        "uvicorn",
        "_machine_studio_server:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    full_env = {**os.environ, **env_vars}
    try:
        subprocess.run(cmd, cwd=str(root), env=full_env)
    finally:
        studio_server_file.unlink(missing_ok=True)
