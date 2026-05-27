"""Shared Studio UI helpers and context builders."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from studio_support.dependencies import get_machine

STUDIO_DIR = Path(__file__).parent
TEMPLATES_DIR = STUDIO_DIR / "templates"
CONFIG_PLUGIN_DIR = Path.home() / ".config" / "machine-core" / "plugins"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

THEMES = {
    "atlas": {
        "label": "Atlas",
        "description": "Structured sans theme with a teal accent.",
    },
    "ledger": {
        "label": "Ledger",
        "description": "Editorial serif-aware theme with a blue accent.",
    },
}

NAVIGATION = [
    {
        "section": "Core",
        "items": [
            {
                "key": "dashboard",
                "label": "Dashboard",
                "href": "/_studio/",
                "icon": "dashboard",
            },
            {
                "key": "registry",
                "label": "Registry",
                "href": "/_studio/registry",
                "icon": "blocks",
            },
            {
                "key": "config",
                "label": "Config",
                "href": "/_studio/config",
                "icon": "settings",
            },
            {
                "key": "services",
                "label": "Services",
                "href": "/_studio/services",
                "icon": "pulse",
            },
            {
                "key": "api",
                "label": "API Surface",
                "href": "/_studio/api",
                "icon": "brackets",
            },
            {"key": "docs", "label": "Docs", "href": "/_studio/docs", "icon": "book"},
        ],
    },
    {
        "section": "Runtime",
        "items": [
            {
                "key": "agents",
                "label": "Agents",
                "href": "/_studio/agents",
                "icon": "spark",
            },
            {
                "key": "tools",
                "label": "Tools",
                "href": "/_studio/tools",
                "icon": "tool",
            },
            {
                "key": "workflows",
                "label": "Workflows",
                "href": "/_studio/workflows",
                "icon": "flow",
            },
            {
                "key": "chat",
                "label": "Chat",
                "href": "/_studio/chat",
                "icon": "message",
            },
        ],
    },
    {
        "section": "Data",
        "items": [
            {
                "key": "memory",
                "label": "Memory",
                "href": "/_studio/sections/memory",
                "icon": "stack",
                "status": "planned",
            },
            {
                "key": "rag",
                "label": "RAG",
                "href": "/_studio/sections/rag",
                "icon": "search",
                "status": "planned",
            },
            {
                "key": "evals",
                "label": "Evals",
                "href": "/_studio/sections/evals",
                "icon": "chart",
                "status": "planned",
            },
            {
                "key": "storage",
                "label": "Storage",
                "href": "/_studio/sections/storage",
                "icon": "database",
                "status": "planned",
            },
        ],
    },
    {
        "section": "Infra",
        "items": [
            {
                "key": "deploy",
                "label": "Deploy",
                "href": "/_studio/sections/deploy",
                "icon": "rocket",
                "status": "planned",
            },
            {
                "key": "observe",
                "label": "Observability",
                "href": "/_studio/sections/observe",
                "icon": "eye",
                "status": "planned",
            },
            {
                "key": "auth",
                "label": "Auth",
                "href": "/_studio/sections/auth",
                "icon": "shield",
                "status": "planned",
            },
            {
                "key": "workspace",
                "label": "Workspace",
                "href": "/_studio/sections/workspace",
                "icon": "folder",
                "status": "planned",
            },
        ],
    },
]

SECTION_COPY = {
    "memory": (
        "Memory",
        "Thread history, working memory, and message inspection will live here.",
    ),
    "rag": (
        "RAG",
        "Pipeline controls, chunk inspection, and retrieval tests belong in this surface.",
    ),
    "evals": (
        "Evals",
        "Datasets, scorecards, and run comparisons will graduate into this section.",
    ),
    "storage": (
        "Storage",
        "File backends, uploads, and browsing will attach to this page.",
    ),
    "deploy": (
        "Deploy",
        "Targets, release history, and deployment controls will live here.",
    ),
    "observe": (
        "Observability",
        "Trace search, cost views, and event timelines will attach here.",
    ),
    "auth": ("Auth", "Key management, sessions, and role boundaries will live here."),
    "workspace": (
        "Workspace",
        "Sandbox files, skills, and browser-backed tools will land here.",
    ),
}


def _project_root() -> Path | None:
    root = os.environ.get("MACHINE_CORE_ROOT")
    if not root:
        return None
    path = Path(root)
    return path if path.exists() else None


def _project_config() -> dict[str, Any]:
    root = _project_root()
    if root is None:
        return {}
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("machine-core", {})


def _plugin_manifests() -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    if not CONFIG_PLUGIN_DIR.exists():
        return manifests

    for manifest_path in sorted(CONFIG_PLUGIN_DIR.glob("*/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        data["path"] = str(manifest_path.parent)
        manifests.append(data)
    return manifests


def _describe_item(item: Any) -> str:
    return (
        getattr(item, "description", None)
        or getattr(item, "__doc__", None)
        or item.__class__.__name__
    )


def _runtime_items(category: str) -> list[dict[str, Any]]:
    machine = get_machine()
    if machine is None or not hasattr(machine, "list_category"):
        return []

    items = []
    for name, item in sorted(machine.list_category(category).items()):
        items.append(
            {
                "name": name,
                "description": _describe_item(item),
                "owner": machine.get_owner(category, name)
                if hasattr(machine, "get_owner")
                else None,
                "operations": sorted((machine.get_operations(category) or {}).keys())
                if hasattr(machine, "get_operations")
                else [],
            }
        )
    return items


def machine_snapshot() -> dict[str, Any]:
    machine = get_machine()
    categories = []
    category_counts: dict[str, int] = {}
    if machine is not None and hasattr(machine, "list_categories"):
        categories = sorted(machine.list_categories())
        category_counts = {
            category: len(machine.list_category(category)) for category in categories
        }

    project_config = _project_config()
    manifests = _plugin_manifests()
    loaded_plugins = (
        sorted(getattr(getattr(machine, "plugins", None), "loaded_plugins", []))
        if machine
        else []
    )
    root = _project_root()
    machine_name = getattr(machine, "name", None) or (root.name if root else "Machine")

    return {
        "machine_name": machine_name,
        "organization_name": "Reserved",
        "workspace_name": "Local Workspace",
        "project_name": root.name if root else "No Project",
        "project_targets": [
            {
                "project_name": root.name if root else "No Project",
                "environment": project_config.get("environment", "local"),
                "active": True,
            }
        ],
        "project_root": str(root) if root else None,
        "entry": project_config.get("entry", "src.main:machine"),
        "environment": project_config.get("environment", "local"),
        "project_config": project_config,
        "plugins_declared": project_config.get("plugins", []),
        "plugin_configs": project_config.get("plugin_configs", {}),
        "categories": categories,
        "category_counts": category_counts,
        "loaded_plugins": loaded_plugins,
        "manifests": manifests,
        "runtime_agents": _runtime_items("agent"),
        "runtime_tools": _runtime_items("tool"),
        "runtime_workflows": _runtime_items("workflow"),
    }


def studio_layout(page_title: str, active_nav: str) -> dict[str, Any]:
    snapshot = machine_snapshot()
    return {
        **snapshot,
        "page_title": page_title,
        "active_nav": active_nav,
        "nav_sections": NAVIGATION,
        "themes": THEMES,
        "section_copy": SECTION_COPY,
    }


def render_template(
    request: Request,
    template_name: str,
    *,
    page_title: str,
    active_nav: str,
    **context: Any,
):
    merged = studio_layout(page_title=page_title, active_nav=active_nav)
    merged.update(context)
    merged["request"] = request
    return templates.TemplateResponse(request, template_name, context=merged)
