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


def _plugin_name_aliases(name: str) -> tuple[str, ...]:
    aliases = [name]
    if "-" in name:
        aliases.append(name.replace("-", "_"))
    if "_" in name:
        aliases.append(name.replace("_", "-"))
    return tuple(dict.fromkeys(aliases))


def _canonical_plugin_name(name: str) -> str:
    return name.replace("-", "_")


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
    canonical_names = {_canonical_plugin_name(name) for name in installed}
    for name in sorted(canonical_names):
        typer.echo(f"  {name}")


@plugin_app.command("install")
def install_plugin(
    name: str = typer.Argument(
        None, help="Plugin name from registry (e.g. agent_support)"
    ),
    force: bool = typer.Option(False, "-f", "--force", help="Force reinstall"),
    all_framework: bool = typer.Option(
        False, "--all-framework", help="Install all framework plugins"
    ),
):
    """Install a plugin from the registry."""
    _require_machine_core()

    async def _install():
        installer = PluginInstaller()
        if all_framework:
            client = RegistryClient()
            plugins = await client.list_plugins(tier="framework")
            for p in plugins:
                try:
                    path = await installer.install(p.name, force=force)
                    typer.echo(f"  ✓ {p.name} → {path}")
                except Exception as e:
                    typer.echo(f"  ✗ {p.name}: {e}")
            typer.echo(f"\nInstalled {len(plugins)} framework plugins.")
        elif name:
            try:
                path = await installer.install(name, force=force)
                typer.echo(f"Installed {name} → {path}")
            except ValueError as e:
                typer.echo(f"Error: {e}")
                raise typer.Exit(1)
        else:
            typer.echo("Error: provide a plugin name or use --all-framework")
            raise typer.Exit(1)

    asyncio.run(_install())


@plugin_app.command("remove")
def remove_plugin(name: str = typer.Argument(..., help="Plugin name to remove")):
    """Remove an installed plugin."""
    _require_machine_core()

    async def _remove():
        installer = PluginInstaller()
        await installer.uninstall(name)
        for alias in _plugin_name_aliases(name):
            if alias == name:
                continue
            await installer.uninstall(alias)
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
