"""Shared Studio UI helpers and context builders."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from studio_support.dependencies import get_machine, get_studio_state
from studio_support.runtime_access import item_operations, item_owner

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
            {
                "key": "account",
                "label": "Account",
                "href": "/_studio/account",
                "icon": "user",
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
    try:
        machine = get_machine()
    except RuntimeError:
        machine = None
    if machine is None or not hasattr(machine, "list_category"):
        return []

    items = []
    for name, item in sorted(machine.list_category(category).items()):
        items.append(
            {
                "name": name,
                "description": _describe_item(item),
                "owner": item_owner(category, name),
                "operations": item_operations(category),
            }
        )
    return items


def _context_snapshot() -> dict[str, Any]:
    try:
        state = get_studio_state()
    except RuntimeError:
        return {
            "tenant_slug": None,
            "tenant_name": None,
            "tenant_options": [],
            "project_slug": None,
            "project_name": None,
            "project_options": [],
            "environment": None,
            "environment_status": None,
            "environment_options": [],
            "entry": None,
            "attachment_status": "detached",
            "attachment_error": None,
            "attachment_machine_name": None,
            "project_targets": [],
        }

    catalog = state.catalog
    active_context = catalog.active_context
    attachment = state.attachment_manager.attachment()

    tenants_by_id = {tenant.id: tenant for tenant in catalog.tenants}
    projects_by_id = {project.id: project for project in catalog.projects}
    environments_by_id = {
        environment.id: environment for environment in catalog.environments
    }

    tenant = tenants_by_id.get(active_context.tenant_id)
    project = projects_by_id.get(active_context.project_id)
    environment = environments_by_id.get(active_context.environment_id)

    project_targets = []
    projects_for_tenant = []
    environments_for_project = []
    for listed_project in catalog.projects:
        listed_tenant = tenants_by_id.get(listed_project.tenant_id)
        if listed_project.tenant_id == active_context.tenant_id:
            projects_for_tenant.append(
                {
                    "slug": listed_project.slug,
                    "name": listed_project.name,
                    "active": listed_project.id == active_context.project_id,
                }
            )
        for listed_environment in catalog.environments:
            if listed_environment.project_id != listed_project.id:
                continue
            if listed_project.id == active_context.project_id:
                environments_for_project.append(
                    {
                        "name": listed_environment.name,
                        "status": listed_environment.status,
                        "active": listed_environment.id
                        == active_context.environment_id,
                    }
                )
            project_targets.append(
                {
                    "tenant_slug": listed_tenant.slug if listed_tenant else None,
                    "tenant_name": listed_tenant.name
                    if listed_tenant
                    else listed_project.tenant_id,
                    "project_slug": listed_project.slug,
                    "project_name": listed_project.name,
                    "environment": listed_environment.name,
                    "environment_status": listed_environment.status,
                    "entry": listed_project.entry,
                    "active": (
                        listed_project.id == active_context.project_id
                        and listed_environment.id == active_context.environment_id
                    ),
                }
            )

    return {
        "tenant_slug": tenant.slug if tenant else None,
        "tenant_name": tenant.name if tenant else None,
        "tenant_options": [
            {
                "slug": listed_tenant.slug,
                "name": listed_tenant.name,
                "active": listed_tenant.id == active_context.tenant_id,
            }
            for listed_tenant in catalog.tenants
        ],
        "project_slug": project.slug if project else None,
        "project_name": project.name if project else None,
        "project_options": projects_for_tenant,
        "environment": environment.name if environment else None,
        "environment_status": environment.status if environment else None,
        "environment_options": environments_for_project,
        "entry": project.entry if project else None,
        "attachment_status": attachment.status,
        "attachment_error": attachment.error,
        "attachment_machine_name": attachment.machine_name,
        "project_targets": project_targets,
    }


def machine_snapshot() -> dict[str, Any]:
    try:
        machine = get_machine()
    except RuntimeError:
        machine = None
    categories = []
    category_counts: dict[str, int] = {}
    if machine is not None and hasattr(machine, "list_categories"):
        categories = sorted(machine.list_categories())
        category_counts = {
            category: len(machine.list_category(category)) for category in categories
        }

    project_config = _project_config()
    context = _context_snapshot()
    manifests = _plugin_manifests()
    loaded_plugins = (
        sorted(getattr(getattr(machine, "plugins", None), "loaded_plugins", []))
        if machine
        else []
    )
    root = _project_root()
    project_name = context["project_name"] or "Unknown project"
    environment = context["environment"] or "No environment"
    entry = context["entry"] or "No entry"
    machine_name = context["attachment_machine_name"] or getattr(machine, "name", None)
    if machine_name is None:
        machine_name = "No runtime attached"
    project_targets = context["project_targets"]

    return {
        "machine_name": machine_name,
        "tenant_slug": context["tenant_slug"],
        "tenant_name": context["tenant_name"] or "Unknown tenant",
        "tenant_options": context["tenant_options"],
        "organization_name": context["tenant_name"] or "Unknown tenant",
        "workspace_name": "Local Workspace",
        "project_slug": context["project_slug"],
        "project_name": project_name,
        "project_options": context["project_options"],
        "project_targets": project_targets,
        "project_root": str(root) if root else None,
        "entry": entry,
        "environment": environment,
        "environment_status": context["environment_status"],
        "environment_options": context["environment_options"],
        "attachment_status": context["attachment_status"],
        "attachment_error": context["attachment_error"],
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
