"""Tests for FastAPI dependency injection."""

import pytest


def test_get_machine_returns_injected_instance(mock_machine):
    from machine_core.plugins.server_support.dependencies import (
        get_machine,
        set_machine,
    )

    set_machine(mock_machine)
    result = get_machine()
    assert result is mock_machine
    assert "chat" in result.list_category("agent")


def test_get_machine_raises_if_not_set():
    from machine_core.plugins.server_support.dependencies import get_machine, _state

    _state["machine"] = None
    with pytest.raises(RuntimeError, match="Machine instance not initialized"):
        get_machine()
