"""Studio plugin store routes.

Exposes the registry catalog and installs/removes plugins **into the current
project**: adds the dependency, declares it in ``[tool.machine-core].plugins``,
and syncs manifests so the runtime picks it up.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/store", tags=["studio-store"])


def _project_root() -> Path:
    return Path(os.environ.get("MACHINE_CORE_ROOT") or ".").resolve()


def _store():
    try:
        from machine_core.plugin.store import PluginStore
    except ImportError as error:  # pragma: no cover - machine-core is a dependency
        raise HTTPException(
            status_code=503, detail=f"Plugin store unavailable: {error}"
        ) from error
    return PluginStore(_project_root())


class StoreInstallRequest(BaseModel):
    name: str
    dev: bool = False


@router.get("")
async def store_catalog() -> dict[str, object]:
    store = _store()
    try:
        plugins = await store.catalog()
    except Exception as error:  # noqa: BLE001 - surface a helpful message
        raise HTTPException(
            status_code=502, detail=f"Could not load the plugin registry: {error}"
        ) from error
    return {
        "project_root": str(store.project_root),
        "has_pyproject": store.pyproject.exists(),
        "declared": store.declared_plugins(),
        "installed": store.installed_plugins(),
        "plugins": plugins,
    }


@router.post("/install")
async def store_install(payload: StoreInstallRequest) -> dict[str, object]:
    store = _store()
    try:
        result = await store.install(payload.name, dev=payload.dev)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {
        "name": result.name,
        "declared": result.declared,
        "installed": result.installed,
        "commands": result.commands,
        "output": result.output[-4000:],
    }


@router.post("/uninstall")
async def store_uninstall(payload: StoreInstallRequest) -> dict[str, object]:
    store = _store()
    try:
        result = await store.uninstall(payload.name)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {
        "name": result.name,
        "declared": result.declared,
        "installed": result.installed,
        "commands": result.commands,
        "output": result.output[-4000:],
    }
