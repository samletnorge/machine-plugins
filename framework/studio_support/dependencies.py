"""Studio dependencies — Machine instance management."""

from __future__ import annotations
from typing import Any

_machine_instance: Any = None


def set_machine(machine: Any) -> None:
    global _machine_instance
    _machine_instance = machine


def get_machine() -> Any:
    return _machine_instance
