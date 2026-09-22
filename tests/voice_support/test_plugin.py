"""Tests for VoiceSupportPlugin and manifest."""

import json
from pathlib import Path

from tests.conftest import WORKSPACE_ROOT

MANIFEST_PATH = WORKSPACE_ROOT / "framework" / "voice_support" / "manifest.json"


class TestManifest:
    def test_manifest_exists(self):
        assert MANIFEST_PATH.exists()

    def test_manifest_valid_json(self):
        data = json.loads(MANIFEST_PATH.read_text())
        assert data["name"] == "voice_support"
        assert data["schema_version"] == "1.0.0"
        assert data["language"] == "python"
        assert "categories:define" in data["capabilities"]
        assert data["transport"]["entry_point"] == "voice_support:VoiceSupportPlugin"


class TestVoiceSupportPlugin:
    def test_import(self):
        from voice_support import VoiceSupportPlugin

        assert VoiceSupportPlugin() is not None

    async def test_initialize(self):
        from voice_support import VoiceSupportPlugin

        await VoiceSupportPlugin().initialize()

    async def test_shutdown(self):
        from voice_support import VoiceSupportPlugin

        await VoiceSupportPlugin().shutdown()
