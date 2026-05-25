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

try:
    from server_support.app import create_app
except ImportError:
    raise ImportError(
        "server-support plugin is required for 'machine dev'.\n"
        "Install it: uv pip install 'git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/server_support'"
    )

app = create_app(machine)

try:
    from machine_studio.app import create_studio_app

    studio = create_studio_app(machine)
    app.mount("/_studio", studio)
except ImportError:
    pass  # Studio extras not installed
