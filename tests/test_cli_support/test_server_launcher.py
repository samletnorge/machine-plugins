"""Tests for CLI server auto-launch behavior."""

import httpx

from cli_support._server_launcher import is_server_running


def test_is_server_running_tolerates_read_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ReadError("connection reset")

    monkeypatch.setattr("cli_support._server_launcher.httpx.get", boom)

    assert is_server_running("http://127.0.0.1:8008") is False
