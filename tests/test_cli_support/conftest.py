"""Shared fixtures for CLI tests."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary directory simulating a project root."""
    return tmp_path


@pytest.fixture
def mock_machine_project(tmp_path):
    """Create a tmp dir with a minimal pyproject.toml containing machine-core config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.machine-core]
entry = "src.main:machine"
""")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")
    (src_dir / "main.py").write_text("""
from machine_core import Machine
machine = Machine(name="test")
""")
    (src_dir / "agents").mkdir()
    (src_dir / "agents" / "__init__.py").write_text("")
    (src_dir / "tools").mkdir()
    (src_dir / "tools" / "__init__.py").write_text("")
    return tmp_path
