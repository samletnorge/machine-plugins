"""Studio FastAPI sub-application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from machine_core.plugins.studio_support.dependencies import set_machine, get_machine

STUDIO_DIR = Path(__file__).parent
TEMPLATES_DIR = STUDIO_DIR / "templates"
STATIC_DIR = STUDIO_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_studio_app(machine: Any) -> FastAPI:
    """Create the Studio FastAPI sub-application."""
    set_machine(machine)

    app = FastAPI(title="Machine Studio", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index(request: Request):
        m = get_machine()
        agents = (
            list(m.list_category("agent").values())
            if hasattr(m, "list_category")
            else list(getattr(m, "agents", {}).values())
        )
        tools = (
            list(m.list_category("tool").values())
            if hasattr(m, "list_category")
            else list(getattr(m, "tools", {}).values())
        )
        workflows = (
            list(m.list_category("workflow").values())
            if hasattr(m, "list_category")
            else list(getattr(m, "workflows", {}).values())
        )
        categories = m.list_categories() if hasattr(m, "list_categories") else []

        return templates.TemplateResponse(
            request,
            "index.html",
            context={
                "machine_name": getattr(m, "name", "Machine"),
                "agents": agents,
                "tools": tools,
                "workflows": workflows,
                "categories": categories,
            },
        )

    from machine_core.plugins.studio_support.routes import chat, tools as tool_routes

    app.include_router(chat.router)
    app.include_router(tool_routes.router)

    return app
