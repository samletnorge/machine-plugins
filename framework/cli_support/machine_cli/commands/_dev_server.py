"""Dev server wrapper — loaded by uvicorn during `machine dev`."""

from __future__ import annotations
import os
import sys

entry = os.environ.get("MACHINE_CORE_ENTRY", "src.main:machine")
root = os.environ.get("MACHINE_CORE_ROOT", ".")

if root not in sys.path:
    sys.path.insert(0, root)

module_path, _, attr_name = entry.rpartition(":")
import importlib

module = importlib.import_module(module_path)
machine = getattr(module, attr_name)

# Create a minimal FastAPI dev server that exposes the machine instance
from fastapi import FastAPI

app = FastAPI(title="machine-core dev server")


@app.get("/health")
async def health():
    """Health check showing loaded plugins and categories."""
    categories = {}
    for cat_name, items in machine._registry.items():
        categories[cat_name] = {
            "items": list(items.keys()),
            "count": len(items),
        }
    return {
        "status": "ok",
        "categories": categories,
        "plugins": [p.name for p in machine.plugins._loaded]
        if hasattr(machine.plugins, "_loaded")
        else [],
    }


@app.get("/")
async def root_info():
    return {"name": "machine-core", "version": "0.9.0", "server": "dev"}
