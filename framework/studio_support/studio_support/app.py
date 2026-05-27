"""Studio FastAPI sub-application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from studio_support.dependencies import set_machine


def create_studio_app(machine: Any) -> FastAPI:
    """Create the Studio FastAPI sub-application."""
    set_machine(machine)

    app = FastAPI(title="Machine Studio", docs_url=None, redoc_url=None)
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from studio_support.routes import (
        chat,
        config,
        dashboard,
        registry,
        resources,
        services,
        tools as tool_routes,
    )

    app.include_router(dashboard.router)
    app.include_router(registry.router)
    app.include_router(config.router)
    app.include_router(services.router)
    app.include_router(resources.router)
    app.include_router(chat.router)
    app.include_router(tool_routes.router)

    return app
