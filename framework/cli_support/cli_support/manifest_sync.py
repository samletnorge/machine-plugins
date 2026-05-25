"""Sync plugin manifests from site-packages to ~/.config/machine-core/plugins/.

This keeps machine-core's plugin discovery (which reads from the config dir)
in sync with what's actually installed in the project's virtualenv.
"""

from __future__ import annotations

import json
import shutil
import site
import sys
from pathlib import Path

from rich.console import Console

console = Console()

CONFIG_DIR = Path.home() / ".config" / "machine-core" / "plugins"


def get_site_packages() -> list[Path]:
    """Get all site-packages directories for the current interpreter."""
    paths = []
    for p in site.getsitepackages():
        pp = Path(p)
        if pp.is_dir():
            paths.append(pp)
    # Also check user site
    user_site = site.getusersitepackages()
    if isinstance(user_site, str):
        pp = Path(user_site)
        if pp.is_dir():
            paths.append(pp)
    return paths


def find_manifests_in_venv(project_root: Path | None = None) -> list[tuple[str, Path]]:
    """Find all manifest.json files in installed packages.

    Returns list of (plugin_name, manifest_path) tuples.
    """
    found = []
    site_dirs = get_site_packages()

    # Also check the project venv directly if available
    if project_root:
        venv_dir = project_root / ".venv"
        if venv_dir.is_dir():
            # Find site-packages in the venv
            for lib_dir in venv_dir.glob("lib/python*/site-packages"):
                if lib_dir.is_dir() and lib_dir not in site_dirs:
                    site_dirs.append(lib_dir)

    for sp in site_dirs:
        # Look for manifest.json inside any package directory
        for manifest in sp.glob("*/manifest.json"):
            try:
                data = json.loads(manifest.read_text())
                name = data.get("name")
                if name and data.get("schema_version"):
                    found.append((name, manifest))
            except (json.JSONDecodeError, OSError):
                continue

    return found


def sync_manifests(project_root: Path | None = None, verbose: bool = True) -> int:
    """Sync manifests from site-packages to ~/.config/machine-core/plugins/.

    Returns number of manifests synced.
    """
    manifests = find_manifests_in_venv(project_root)

    if not manifests:
        if verbose:
            console.print(
                "[yellow]No plugin manifests found in site-packages.[/yellow]"
            )
        return 0

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    synced = 0

    for name, manifest_path in manifests:
        target_dir = CONFIG_DIR / name
        target_file = target_dir / "manifest.json"

        # Only copy if newer or missing
        if target_file.exists():
            existing = target_file.read_text()
            new = manifest_path.read_text()
            if existing == new:
                continue

        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, target_file)
        synced += 1
        if verbose:
            console.print(f"  [dim]Synced:[/dim] {name}")

    if verbose and synced:
        console.print(f"[green]Synced {synced} plugin manifest(s).[/green]")

    return synced
