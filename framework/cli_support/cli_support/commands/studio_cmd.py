"""machine studio — launch the Studio web UI."""

from __future__ import annotations

import os
import subprocess
import sys
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
    python_executable = str(venv_python) if venv_python.exists() else sys.executable
    if not venv_python.exists():
        console.print(
            "[yellow]No project .venv found. Falling back to the current machine CLI interpreter.[/yellow]"
        )

    console.print(f"[green]Starting Machine Studio...[/green]")
    console.print(f"  URL: http://{host}:{port}/_studio/")
    console.print(f"  Entry: {entry}")

    env_vars = {
        "MACHINE_CORE_ENTRY": entry,
        "MACHINE_CORE_ROOT": str(root),
        "MACHINE_STUDIO_ENABLED": "1",
    }
    parent_root = root.parent
    pythonpath_entries = [str(parent_root), str(root)]
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env_vars["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    studio_site_packages = _resolve_studio_source_path(studio_support.__file__)

    studio_server_code = f'''\
"""Auto-generated studio server for machine studio. Do not edit."""
import os, sys
sys.path.insert(0, os.environ.get("MACHINE_CORE_ROOT", "."))
sys.path.insert(0, {str(studio_site_packages)!r})
import importlib
import importlib.util
from pathlib import Path

def _load_entry_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        root = Path(os.environ.get("MACHINE_CORE_ROOT", ".")).resolve()
        module_path = Path(*module_name.split("."))
        file_candidates = [module_path.with_suffix(".py"), module_path / "__init__.py"]
        for base in [root, *root.parents]:
            for relative_path in file_candidates:
                candidate = base / relative_path
                if not candidate.exists():
                    continue
                spec = importlib.util.spec_from_file_location(module_name, candidate)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module
        raise exc

module = _load_entry_module("{entry.rpartition(":")[0]}")
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
        python_executable,
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
