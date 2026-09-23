"""Shared CLI utilities."""

from __future__ import annotations

import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


def to_identifier(name: str) -> str:
    """Convert an arbitrary name into a valid Python identifier."""
    ident = re.sub(r"\W", "_", name)
    if not ident:
        return "generated"
    if ident[0].isdigit():
        return f"_{ident}"
    return ident


def to_class_name(name: str) -> str:
    """Convert a name into a PascalCase class name."""
    parts = re.split(r"[^0-9a-zA-Z]+", name)
    return "".join(part[:1].upper() + part[1:] for part in parts if part) or "Generated"


def to_const_name(name: str) -> str:
    """Convert a name into an UPPER_SNAKE_CASE constant name."""
    return re.sub(r"\W", "_", name).upper() or "GENERATED"


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default cwd) looking for pyproject.toml with [tool.machine-core]."""
    current = start or Path.cwd()
    for parent in [current, *current.parents]:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            if "tool" in data and "machine-core" in data["tool"]:
                return parent
    return None


def load_machine_config(project_root: Path) -> dict[str, Any]:
    """Load [tool.machine-core] from pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("machine-core", {})


def load_machine_instance(project_root: Path):
    """Import and return the Machine instance from the configured entry point."""
    config = load_machine_config(project_root)
    entry = config.get("entry", "src.main:machine")
    module_path, _, attr_name = entry.rpartition(":")
    if not module_path or not attr_name:
        console.print(f"[red]Invalid entry point: {entry}[/red]")
        raise SystemExit(1)

    str_root = str(project_root)
    if str_root not in sys.path:
        sys.path.insert(0, str_root)

    import importlib

    # Drop any previously imported entry modules so the configured entry point
    # is always executed fresh from *this* project root. CLI invocations may
    # share a process with other projects (e.g. during tests), and a cached
    # top-level package would otherwise point at the wrong project.
    importlib.invalidate_caches()
    top_level = module_path.split(".")[0]
    for mod_name in list(sys.modules):
        if mod_name == top_level or mod_name.startswith(f"{top_level}."):
            sys.modules.pop(mod_name, None)

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        console.print(f"[red]Cannot import {module_path}: {e}[/red]")
        raise SystemExit(1)
    except Exception as e:  # noqa: BLE001 - surface a clear CLI error
        console.print(
            f"[red]Error while importing {module_path}: {type(e).__name__}: {e}[/red]"
        )
        raise SystemExit(1)

    machine = getattr(module, attr_name, None)
    if machine is None:
        console.print(f"[red]{attr_name} not found in {module_path}[/red]")
        raise SystemExit(1)

    return machine
