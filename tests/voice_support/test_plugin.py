"""Tests for VoiceSupportPlugin and manifest."""

import json
import pytest
from pathlib import Path


class TestManifest:
    def test_manifest_exists(self):
        manifest_path = Path("src/machine_core/plugins/voice_support/manifest.json")
        assert manifest_path.exists()

    def test_manifest_valid_json(self):
        manifest_path = Path("src/machine_core/plugins/voice_support/manifest.json")
        data = json.loads(manifest_path.read_text())
        assert data["name"] == "voice-support"
        assert data["schema_version"] == "1.0.0"
        assert data["language"] == "python"
        assert "categories:define" in data["capabilities"]
        assert (
            "machine_core.plugins.voice_support:VoiceSupportPlugin"
            in data["transport"]["entry_point"]
        )


class TestVoiceSupportPlugin:
    def test_import(self):
        from machine_core.plugins.voice_support import VoiceSupportPlugin

        plugin = VoiceSupportPlugin()
        assert plugin is not None

    @pytest.mark.asyncio
    async def test_initialize(self):
        from machine_core.plugins.voice_support import VoiceSupportPlugin

        plugin = VoiceSupportPlugin()
        await plugin.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        from machine_core.plugins.voice_support import VoiceSupportPlugin

        plugin = VoiceSupportPlugin()
        await plugin.shutdown()
