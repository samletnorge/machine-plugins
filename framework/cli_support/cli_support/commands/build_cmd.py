"""machine build — validate and build for production."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape

from cli_support.utils import (
    find_project_root,
    load_machine_config,
    load_machine_instance,
)

console = Console()


def _fail(message: str) -> None:
    """Print a build failure and exit non-zero."""
    console.print(f"[red]✗ Build error: {escape(str(message))}[/red]")
    raise typer.Exit(code=1)


def _plugin_aliases(name: str) -> set[str]:
    return {name, name.replace("-", "_"), name.replace("_", "-")}


def _run_uv_build(root: Path) -> None:
    """Run ``uv build`` in the project root, failing loudly on any error."""
    uv = shutil.which("uv")
    if uv is None:
        _fail(
            "'uv' is not installed or not on PATH. Install it from "
            "https://docs.astral.sh/uv/ and re-run 'machine build'."
        )

    console.print("[bold]Building project with 'uv build'...[/bold]")
    try:
        proc = subprocess.run(
            [uv, "build"],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
    except OSError as e:  # pragma: no cover - environment dependent
        _fail(f"could not execute 'uv build': {e}")

    if proc.returncode != 0:
        if proc.stdout.strip():
            console.print(proc.stdout.strip(), markup=False)
        if proc.stderr.strip():
            console.print(proc.stderr.strip(), markup=False)
        _fail(f"'uv build' failed with exit code {proc.returncode}.")

    if proc.stdout.strip():
        console.print(proc.stdout.strip(), markup=False)


def _report_artifacts(root: Path) -> list[Path]:
    """Report the artifacts produced under ``dist/``."""
    dist = root / "dist"
    if not dist.is_dir():
        _fail("'uv build' completed but no dist/ directory was produced.")

    artifacts = sorted(p for p in dist.iterdir() if p.is_file())
    if not artifacts:
        _fail("'uv build' completed but dist/ contains no build artifacts.")

    console.print(f"[green]✓[/green] Build artifacts in {escape(str(dist))}:")
    for artifact in artifacts:
        size_kib = artifact.stat().st_size / 1024
        console.print(f"    {escape(artifact.name)} ({size_kib:.1f} KiB)")
    return artifacts


def _verify_machine(root: Path, declared_plugins: list[str]) -> list[str]:
    """Import the entry point, start the Machine, verify plugins, then stop it."""
    try:
        machine = load_machine_instance(root)
    except SystemExit:
        _fail("could not load the configured entry point (see error above).")
    except Exception as e:  # noqa: BLE001 - surface a clear CLI error
        _fail(f"could not load the configured entry point: {e}")

    if not hasattr(machine, "start"):
        _fail("configured entry point does not expose a Machine (no start() method).")

    async def _start_check_stop() -> list[str]:
        await machine.start()
        try:
            loaded = set(machine.plugins.loaded_plugins)
            missing = [
                plugin
                for plugin in declared_plugins
                if not _plugin_aliases(plugin) & loaded
            ]
            if missing:
                raise RuntimeError(
                    "declared plugin(s) failed to load: " + ", ".join(missing)
                )
            return list(machine.list_categories())
        finally:
            await machine.shutdown()

    try:
        categories = asyncio.run(_start_check_stop())
    except Exception as e:  # noqa: BLE001 - surface a clear CLI error
        _fail(f"Machine failed to start: {e}")

    console.print("[green]✓[/green] Machine starts and shuts down cleanly")
    if declared_plugins:
        console.print(f"    Plugins loaded: {', '.join(declared_plugins)}")
    console.print(f"    Categories: {', '.join(sorted(categories)) or '(none)'}")
    return categories


def build_command():
    """Validate and build for production."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")
    declared_plugins = list(config.get("plugins", []) or [])

    console.print("[bold]Running build checks...[/bold]")

    # Check pyproject.toml
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        console.print("[red]✗ pyproject.toml not found[/red]")
        raise typer.Exit(code=1)
    console.print("[green]✓[/green] pyproject.toml valid")

    # Check entry point
    module_path, _, attr_name = entry.rpartition(":")
    if not module_path or not attr_name:
        console.print(f"[red]✗ Invalid entry point: {entry}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]✓[/green] Entry point: {entry}")

    # Check source directory
    src_dir = root / "src"
    if not src_dir.exists():
        console.print("[red]✗ src/ directory not found[/red]")
        raise typer.Exit(code=1)
    console.print("[green]✓[/green] Source directory exists")

    # Real build + artifact report + runtime verification.
    _run_uv_build(root)
    _report_artifacts(root)
    _verify_machine(root, declared_plugins)

    console.print("\n[green]Build complete![/green]")
