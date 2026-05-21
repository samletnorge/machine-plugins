"""Shared fixtures for workspace tests."""

import tempfile
import shutil
import pytest


@pytest.fixture
def tmp_workspace_dir():
    """Create a clean temporary workspace directory."""
    d = tempfile.mkdtemp(prefix="machine_ws_")
    yield d
    shutil.rmtree(d, ignore_errors=True)
