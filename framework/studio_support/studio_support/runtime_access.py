from __future__ import annotations

from typing import Any

from studio_support.dependencies import get_machine, get_runtime_attachment


def current_runtime_key() -> str:
    attachment = get_runtime_attachment()
    return attachment.context.environment_id


def machine_item(category: str, name: str) -> Any | None:
    machine = get_machine()
    if machine is None:
        return None
    if hasattr(machine, "resolve"):
        return machine.resolve(category, name)
    return getattr(machine, f"{category}s", {}).get(name)


def item_owner(category: str, name: str) -> str | None:
    machine = get_machine()
    if machine is not None and hasattr(machine, "get_owner"):
        return machine.get_owner(category, name)
    return None


def item_operations(category: str) -> list[str]:
    machine = get_machine()
    if machine is not None and hasattr(machine, "get_operations"):
        return sorted((machine.get_operations(category) or {}).keys())
    return []
