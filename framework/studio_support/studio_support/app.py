"""Studio FastAPI sub-application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from studio_support.dependencies import (
    bind_studio_state,
    build_studio_state,
    reset_bound_studio_state,
)


def create_studio_app(machine: Any) -> FastAPI:
    """Create the Studio FastAPI sub-application."""
    studio_state = build_studio_state(machine)

    app = FastAPI(title="Machine Studio", docs_url=None, redoc_url=None)
    app.state.studio_state = studio_state

    @app.middleware("http")
    async def inject_studio_state(request, call_next):
        token = bind_studio_state(request.app.state.studio_state)
        try:
            return await call_next(request)
        finally:
            reset_bound_studio_state(token)

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
    from studio_support.control import config as control_config
    from studio_support.control import registry as control_registry
    from studio_support.control import services as control_services
    from studio_support.control import auth as control_auth
    from studio_support.control import browser as control_browser
    from studio_support.control import context as control_context
    from studio_support.control import deploy as control_deploy
    from studio_support.control import evals as control_evals
    from studio_support.control import memory as control_memory
    from studio_support.control import observe as control_observe
    from studio_support.control import pubsub as control_pubsub
    from studio_support.control import rag as control_rag
    from studio_support.control import storage as control_storage
    from studio_support.control import runtime as control_runtime
    from studio_support.control import voice as control_voice
    from studio_support.control import workspace as control_workspace

    app.include_router(dashboard.router)
    app.include_router(registry.router)
    app.include_router(config.router)
    app.include_router(services.router)
    app.include_router(resources.router)
    app.include_router(chat.router)
    app.include_router(tool_routes.router)
    app.include_router(control_services.router)
    app.include_router(control_registry.router)
    app.include_router(control_config.router)
    app.include_router(control_context.router)
    app.include_router(control_runtime.router)
    app.include_router(control_deploy.router)
    app.include_router(control_auth.router)
    app.include_router(control_observe.router)
    app.include_router(control_memory.router)
    app.include_router(control_rag.router)
    app.include_router(control_evals.router)
    app.include_router(control_pubsub.router)
    app.include_router(control_storage.router)
    app.include_router(control_workspace.router)
    app.include_router(control_browser.router)
    app.include_router(control_voice.router)

    return app
