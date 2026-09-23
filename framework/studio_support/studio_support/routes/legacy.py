"""Legacy Studio UI routes.

The Studio UI is now a SvelteKit SPA served at ``/_studio/app``. Every legacy
server-rendered page permanently redirects into the SPA so old links keep
working, while the control-plane JSON API under ``/_studio/api`` is unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["studio-legacy"], include_in_schema=False)

# Legacy page -> SPA path (relative to /_studio/app).
_PAGE_REDIRECTS: dict[str, str] = {
    "/": "/",
    "/dashboard": "/",
    "/account": "/context",
    "/registry": "/registry",
    "/config": "/config",
    "/services": "/services",
    "/api": "/services",
    "/agents": "/runtime",
    "/tools": "/runtime",
    "/workflows": "/runtime",
    "/chat": "/runtime",
    "/docs": "/",
}

_DOMAIN_KEYS = {
    "memory",
    "rag",
    "evals",
    "storage",
    "deploy",
    "observe",
    "auth",
    "workspace",
    "browser",
    "voice",
    "pubsub",
}


def _app_url(request: Request, path: str = "") -> str:
    root = request.scope.get("root_path", "") or ""
    return f"{root}/app{path}"


def _redirect(request: Request, path: str = "") -> RedirectResponse:
    return RedirectResponse(_app_url(request, path), status_code=307)


@router.get("/")
async def legacy_index(request: Request) -> RedirectResponse:
    return _redirect(request, "/")


@router.get("/dashboard")
async def legacy_dashboard(request: Request) -> RedirectResponse:
    return _redirect(request, "/")


@router.get("/account")
async def legacy_account(request: Request) -> RedirectResponse:
    return _redirect(request, "/context")


@router.get("/registry")
async def legacy_registry(request: Request) -> RedirectResponse:
    return _redirect(request, "/registry")


@router.get("/config")
async def legacy_config(request: Request) -> RedirectResponse:
    return _redirect(request, "/config")


@router.get("/services")
async def legacy_services(request: Request) -> RedirectResponse:
    return _redirect(request, "/services")


@router.get("/api")
async def legacy_api_surface(request: Request) -> RedirectResponse:
    return _redirect(request, "/services")


@router.get("/agents")
async def legacy_agents(request: Request) -> RedirectResponse:
    return _redirect(request, "/runtime")


@router.get("/tools")
async def legacy_tools(request: Request) -> RedirectResponse:
    return _redirect(request, "/runtime")


@router.get("/workflows")
async def legacy_workflows(request: Request) -> RedirectResponse:
    return _redirect(request, "/runtime")


@router.get("/chat")
async def legacy_chat(request: Request) -> RedirectResponse:
    return _redirect(request, "/runtime")


@router.get("/sections/{section_key}")
async def legacy_section(request: Request, section_key: str) -> RedirectResponse:
    if section_key in _DOMAIN_KEYS:
        return _redirect(request, f"/domain/{section_key}")
    return _redirect(request, "/")


@router.get("/islands/{domain}")
async def legacy_island(request: Request, domain: str) -> RedirectResponse:
    if domain in _DOMAIN_KEYS:
        return _redirect(request, f"/domain/{domain}")
    return _redirect(request, "/")


@router.get("/docs")
async def legacy_docs(request: Request) -> RedirectResponse:
    return _redirect(request, "/")


@router.get("/docs/{path:path}")
async def legacy_docs_page(request: Request, path: str) -> RedirectResponse:
    _ = path
    return _redirect(request, "/")
