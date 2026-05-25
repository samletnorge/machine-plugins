"""FastAPI dependency injection for the Machine instance."""

from __future__ import annotations
from typing import Any

_state: dict[str, Any] = {"machine": None}


def set_machine(machine: Any) -> None:
    """Set the Machine instance for dependency injection."""
    _state["machine"] = machine


def get_machine() -> Any:
    """Get the Machine instance. Used as a FastAPI dependency."""
    machine = _state["machine"]
    if machine is None:
        raise RuntimeError(
            "Machine instance not initialized. Call set_machine() first."
        )
    return machine
