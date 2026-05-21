"""Test that server-support plugin is discoverable via builtin_manifests."""


def test_server_support_in_builtin_manifests():
    """server-support must appear in the plugin discovery list."""
    from machine_core.plugins import builtin_manifests

    manifests = builtin_manifests()
    names = [m.name for m in manifests]
    assert "server-support" in names


def test_server_support_manifest_fields():
    """server-support manifest has correct capabilities."""
    from machine_core.plugins import builtin_manifests

    manifests = builtin_manifests()
    manifest = next(m for m in manifests if m.name == "server-support")
    assert manifest.language == "python"
    assert "categories:define" in manifest.capabilities
