"""``machine plugin`` — browse and install registry plugins into a project.

Installing a plugin updates the *project*: it adds the dependency (``uv add``),
declares the plugin in ``[tool.machine-core].plugins``, and keeps the machine
data dir in sync so the runtime loads it on next start.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

try:
    from machine_core.plugin.registry import RegistryClient
    from machine_core.plugin.store import PluginStore
except ImportError:
    RegistryClient = None  # type: ignore[assignment, misc]
    PluginStore = None  # type: ignore[assignment, misc]

plugin_app = typer.Typer(help="Browse and install plugins into this project")


def _require_machine_core() -> None:
    if PluginStore is None:
        typer.echo(
            "Error: machine-core with plugin store support is required. "
            "Upgrade machine-core (uv lock --upgrade-package machine-core)."
        )
        raise typer.Exit(1)


def _require_registry() -> None:
    if RegistryClient is None:
        typer.echo("Error: machine-core registry client is unavailable.")
        raise typer.Exit(1)


def _store(project_root: Path) -> "PluginStore":
    return PluginStore(project_root)


@plugin_app.command("list")
def list_plugins() -> None:
    """List plugins declared in this project and installed locally."""
    _require_machine_core()
    store = _store(Path.cwd())
    declared = store.declared_plugins()
    installed = set(store.installed_plugins())

    typer.echo("Declared in [tool.machine-core].plugins:")
    if not declared:
        typer.echo("  (none)")
    for name in declared:
        marker = "  ✓ installed" if name in installed else "  (not installed)"
        typer.echo(f"  {name}{marker}")

    extra = sorted(installed - set(declared))
    if extra:
        typer.echo("\nInstalled but not declared:")
        for name in extra:
            typer.echo(f"  {name}")


@plugin_app.command("available")
def available(
    tier: str = typer.Option(None, help="Filter by tier (framework, community)"),
) -> None:
    """List plugins available in the registry."""
    _require_machine_core()
    _require_registry()

    async def _run() -> None:
        client = RegistryClient()
        try:
            plugins = await client.list_plugins(tier=tier)
        except Exception as error:  # noqa: BLE001
            typer.echo(f"Error: {error}")
            raise typer.Exit(1)
        for plugin in plugins:
            typer.echo(f"  {plugin.name:32s} [{plugin.tier}] — {plugin.description}")

    asyncio.run(_run())


@plugin_app.command("search")
def search_plugins(query: str = typer.Argument(..., help="Search term")) -> None:
    """Search the plugin registry."""
    _require_machine_core()
    _require_registry()

    async def _run() -> None:
        client = RegistryClient()
        try:
            results = await client.search_plugins(query)
        except Exception as error:  # noqa: BLE001
            typer.echo(f"Error: {error}")
            raise typer.Exit(1)
        if not results:
            typer.echo("No plugins found.")
            return
        for plugin in results:
            typer.echo(f"  {plugin.name:32s} [{plugin.tier}] — {plugin.description}")

    asyncio.run(_run())


@plugin_app.command("add")
def add_plugin(
    name: str = typer.Argument(..., help="Plugin name from the registry"),
    dev: bool = typer.Option(False, "--dev", help="Add as a development dependency"),
) -> None:
    """Install a plugin into this project (dependency + declaration)."""
    _require_machine_core()

    async def _run() -> None:
        store = _store(Path.cwd())
        try:
            result = await store.install(name, dev=dev)
        except Exception as error:  # noqa: BLE001
            typer.echo(f"Error: {error}")
            raise typer.Exit(1)
        typer.echo(f"Installed {result.name}")
        typer.echo("Declared in [tool.machine-core].plugins and added as a dependency.")
        typer.echo("Restart the runtime: machine dev")

    asyncio.run(_run())


@plugin_app.command("install")
def install_alias(
    name: str = typer.Argument(..., help="Plugin name from the registry"),
    dev: bool = typer.Option(False, "--dev", help="Add as a development dependency"),
) -> None:
    """Alias for `machine plugin add`."""
    add_plugin(name, dev)


@plugin_app.command("remove")
def remove_plugin(name: str = typer.Argument(..., help="Plugin name to remove")) -> None:
    """Remove a plugin from this project."""
    _require_machine_core()

    async def _run() -> None:
        store = _store(Path.cwd())
        try:
            await store.uninstall(name)
        except Exception as error:  # noqa: BLE001
            typer.echo(f"Error: {error}")
            raise typer.Exit(1)
        typer.echo(f"Removed {name}")

    asyncio.run(_run())
