"""FastAPI app factory that auto-generates routes from a Machine instance."""

from __future__ import annotations
import uuid
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .dependencies import set_machine


def _mount_routes(app: FastAPI, machine: Any) -> None:
    """Generate and include dynamic routes from the Machine registry."""
    from .route_generator import generate_routes

    api_router = generate_routes(machine)
    app.include_router(api_router)


def create_app(
    machine: Any,
    *,
    title: str = "Machine Core API",
    version: str = "0.1.0",
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create a FastAPI app with auto-generated routes from the Machine registry."""
    set_machine(machine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # If machine hasn't been started yet, start it (loads plugins)
        if hasattr(machine, "start") and not _has_categories(machine):
            await machine.start()
            # Re-generate routes now that plugins are loaded
            _mount_routes(app, machine)

        cats = machine.list_categories() if hasattr(machine, "list_categories") else []
        logger.info(f"Starting Machine Core API — {len(cats)} categories")
        yield
        logger.info("Shutting down Machine Core API")

    app = FastAPI(
        title=title,
        version=version,
        lifespan=lifespan,
        description="Auto-generated API from Machine Core registry.",
    )

    # CORS
    origins = cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    # Health check — dynamic (reads registry at request time)
    @app.get("/health")
    async def health():
        categories = {}
        if hasattr(machine, "list_categories"):
            for cat in machine.list_categories():
                categories[cat] = len(machine.list_category(cat))
        return {"status": "healthy", "categories": categories}

    # If machine already has categories (pre-loaded or test), generate routes now
    if _has_categories(machine):
        _mount_routes(app, machine)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


def _has_categories(machine: Any) -> bool:
    """Check if the machine already has categories registered."""
    if hasattr(machine, "list_categories"):
        return len(machine.list_categories()) > 0
    return False
