"""machine plugin install/remove/list commands."""

from __future__ import annotations

import asyncio

import typer

try:
    from machine_core.plugin.registry import RegistryClient
    from machine_core.plugin.installer import PluginInstaller
except ImportError:
    RegistryClient = None  # type: ignore[assignment, misc]
    PluginInstaller = None  # type: ignore[assignment, misc]

plugin_app = typer.Typer(help="Manage plugins")


def _require_machine_core():
    if RegistryClient is None:
        typer.echo("Error: machine-core is not installed. Install it first.")
        raise typer.Exit(1)


@plugin_app.command("list")
def list_plugins():
    """List installed plugins."""
    _require_machine_core()
    installer = PluginInstaller()
    installed = installer.installed_plugins()
    if not installed:
        typer.echo("No plugins installed.")
        return
    for name in sorted(installed):
        typer.echo(f"  {name}")


@plugin_app.command("install")
def install_plugin(
    name: str = typer.Argument(
        ..., help="Plugin name from registry (e.g. agent_support)"
    ),
    force: bool = typer.Option(False, "-f", "--force", help="Force reinstall"),
):
    """Install a plugin from the registry."""
    _require_machine_core()

    async def _install():
        installer = PluginInstaller()
        try:
            path = await installer.install(name, force=force)
            typer.echo(f"Installed {name} → {path}")
        except ValueError as e:
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)

    asyncio.run(_install())


@plugin_app.command("remove")
def remove_plugin(name: str = typer.Argument(..., help="Plugin name to remove")):
    """Remove an installed plugin."""
    _require_machine_core()

    async def _remove():
        installer = PluginInstaller()
        await installer.uninstall(name)
        typer.echo(f"Removed {name}")

    asyncio.run(_remove())


@plugin_app.command("search")
def search_plugins(query: str = typer.Argument(..., help="Search term")):
    """Search the plugin registry."""
    _require_machine_core()

    async def _search():
        client = RegistryClient()
        results = await client.search_plugins(query)
        if not results:
            typer.echo("No plugins found.")
            return
        for p in results:
            typer.echo(f"  {p.name:30s} [{p.tier}] — {p.description}")

    asyncio.run(_search())
