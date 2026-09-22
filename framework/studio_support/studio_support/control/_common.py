"""Shared helpers for Studio control-plane routers.

Control domains expose what is actually installed in the active runtime's
Machine registry, mirroring the "show everything / not installed" pattern from
the Mission Control spec.
"""

from __future__ import annotations

from typing import Any

from studio_support.dependencies import get_machine
from studio_support.runtime_access import item_operations, item_owner


def _describe(impl: Any) -> str:
    description = getattr(impl, "description", None) or getattr(impl, "__doc__", None)
    if description:
        return str(description).strip()
    return impl.__class__.__name__


def category_items(category: str) -> list[dict[str, Any]]:
    """List the registered items for a category with owner and operations."""
    machine = get_machine()
    if machine is None or not hasattr(machine, "list_category"):
        return []
    items: list[dict[str, Any]] = []
    for name, impl in sorted(machine.list_category(category).items()):
        items.append(
            {
                "name": name,
                "owner": item_owner(category, name),
                "description": _describe(impl),
                "operations": item_operations(category),
            }
        )
    return items


def domain_payload(domain: str, categories: list[str]) -> dict[str, Any]:
    """Build a control-plane payload for a domain backed by categories."""
    catalog = {category: category_items(category) for category in categories}
    installed = any(catalog.values())
    primary = categories[0] if categories else None
    return {
        "domain": domain,
        "installed": installed,
        "implemented": installed,
        "categories": catalog,
        "items": catalog.get(primary, []) if primary else [],
    }
