"""Test that the server plugin is discoverable from the workspace."""

from tests.conftest import discover_manifests


def test_server_support_is_discoverable():
    """server_support must appear in the workspace discovery list."""
    names = {m.name for m in discover_manifests()}
    assert "server_support" in names


def test_server_support_manifest_fields():
    """server_support manifest has correct capabilities."""
    manifest = next(m for m in discover_manifests() if m.name == "server_support")
    assert manifest.language == "python"
    assert "categories:define" in manifest.capabilities
