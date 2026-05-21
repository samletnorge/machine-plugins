"""machine plugin install/remove/list commands."""

from __future__ import annotations

import typer
from pathlib import Path

try:
    from machine_core.plugin.registry import RegistryClient
    from machine_core.plugin.installer import PluginInstaller
except ImportError:
    RegistryClient = None  # type: ignore[assignment, misc]
    PluginInstaller = None  # type: ignore[assignment, misc]

plugin_app = typer.Typer(help="Manage plugins")

DEFAULT_REGISTRY_DIR = Path.home() / ".config" / "machine-core" / "registry"
DEFAULT_INSTALL_DIR = Path.home() / ".config" / "machine-core" / "installed"


def _require_machine_core():
    if RegistryClient is None:
        typer.echo("Error: machine-core is not installed. Install it first.")
        raise typer.Exit(1)


@plugin_app.command("list")
def list_plugins():
    """List installed plugins."""
    if not DEFAULT_INSTALL_DIR.exists():
        typer.echo("No plugins installed.")
        return
    for p in sorted(DEFAULT_INSTALL_DIR.iterdir()):
        if p.is_dir() and not p.name.startswith("_"):
            typer.echo(f"  {p.name}")


@plugin_app.command("install")
def install_plugin(
    name: str = typer.Argument(..., help="Plugin name from registry"),
    interactive: bool = typer.Option(
        False, "-i", "--interactive", help="Launch config wizard"
    ),
):
    """Install a plugin from the registry."""
    _require_machine_core()

    client = RegistryClient(DEFAULT_REGISTRY_DIR)
    plugin = client.get_plugin(name)

    if plugin is None:
        typer.echo(
            f"Plugin '{name}' not found in registry. Run `machine registry update` first?"
        )
        raise typer.Exit(1)

    installer = PluginInstaller(
        registry_dir=DEFAULT_REGISTRY_DIR, install_dir=DEFAULT_INSTALL_DIR
    )

    location = plugin["location"]
    runtime = plugin.get("runtime", "python")

    if location.startswith("manifests/"):
        manifest = client.resolve_manifest(name)
        if manifest is None:
            typer.echo(f"Could not resolve manifest for '{name}'")
            raise typer.Exit(1)
        result = installer.install_from_manifest(manifest)
    else:
        result = installer.install(name, location=location, runtime=runtime)

    if result.success:
        typer.echo(f"Installed {name} → {result.install_path}")
        if interactive:
            from ..tui.app import MachineApp

            app = MachineApp()
            app.run()
    else:
        typer.echo(f"Failed to install {name}: {result.error}")
        raise typer.Exit(1)


@plugin_app.command("remove")
def remove_plugin(name: str = typer.Argument(..., help="Plugin name to remove")):
    """Remove an installed plugin."""
    _require_machine_core()

    installer = PluginInstaller(
        registry_dir=DEFAULT_REGISTRY_DIR, install_dir=DEFAULT_INSTALL_DIR
    )
    result = installer.uninstall(name)
    if result.success:
        typer.echo(f"Removed {name}")
    else:
        typer.echo(f"Failed to remove {name}: {result.error}")


@plugin_app.command("search")
def search_plugins(query: str = typer.Argument(..., help="Search term")):
    """Search the plugin registry."""
    _require_machine_core()

    client = RegistryClient(DEFAULT_REGISTRY_DIR)
    results = client.search(query)
    if not results:
        typer.echo("No plugins found.")
        return
    for p in results:
        typer.echo(
            f"  {p['name']:30s} [{p.get('category', '')}] — {p.get('description', '')}"
        )
