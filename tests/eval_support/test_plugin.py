"""Tests for the EvalSupportPlugin registration."""

import pytest
from eval_support import EvalSupportPlugin


def test_plugin_instantiation():
    """EvalSupportPlugin can be instantiated."""
    plugin = EvalSupportPlugin()
    assert plugin is not None


def test_plugin_has_lifecycle_methods():
    """Plugin has initialize, setup, and shutdown methods."""
    plugin = EvalSupportPlugin()
    assert hasattr(plugin, "initialize")
    assert hasattr(plugin, "setup")
    assert hasattr(plugin, "shutdown")
