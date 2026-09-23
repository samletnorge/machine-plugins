"""Tests for VoiceSupportPlugin and manifest."""

import json
from pathlib import Path

import pytest

from tests.conftest import WORKSPACE_ROOT

MANIFEST_PATH = WORKSPACE_ROOT / "framework" / "voice_support" / "manifest.json"

_CREDENTIAL_ENV_VARS = [
    "OPENAI_API_KEY",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "FISH_AUDIO_API_KEY",
    "DEEPGRAM_API_KEY",
    "ELEVENLABS_API_KEY",
]


class _MockCtx:
    def __init__(self):
        self.categories = {}
        self.items = []

    def register_category(self, name, **kwargs):
        self.categories[name] = kwargs

    def register(self, category, name, impl):
        self.items.append((category, name, impl))


def _clear_credentials(monkeypatch):
    for env in _CREDENTIAL_ENV_VARS:
        monkeypatch.delenv(env, raising=False)


def _registered_names(ctx):
    return {name for cat, name, _ in ctx.items if cat == "voice_provider"}


class TestManifest:
    def test_manifest_exists(self):
        assert MANIFEST_PATH.exists()

    def test_manifest_valid_json(self):
        data = json.loads(MANIFEST_PATH.read_text())
        assert data["name"] == "voice_support"
        assert data["schema_version"] == "1.0.0"
        assert data["language"] == "python"
        assert "categories:define" in data["capabilities"]
        assert "voice_provider:register" in data["capabilities"]
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


@pytest.mark.asyncio
async def test_setup_is_non_broken_without_credentials(monkeypatch):
    """An env-less environment must still yield a working setup."""
    _clear_credentials(monkeypatch)

    from voice_support import VoiceSupportPlugin

    plugin = VoiceSupportPlugin()
    await plugin.initialize(config={})
    ctx = _MockCtx()

    await plugin.setup(ctx)

    assert "voice_provider" in ctx.categories
    names = _registered_names(ctx)
    # Credential-gated providers must not register without keys.
    for keyed in [
        "openai",
        "azure",
        "google_cloud",
        "fish_audio",
        "deepgram",
        "elevenlabs",
    ]:
        assert keyed not in names


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sdk", "provider_name"), [("gtts", "gtts"), ("edge_tts", "edge_tts")]
)
async def test_dependency_free_providers_register_when_available(
    monkeypatch, sdk, provider_name
):
    """gtts / edge_tts need no credentials — they register when installed."""
    pytest.importorskip(sdk)
    _clear_credentials(monkeypatch)

    from voice_support import VoiceSupportPlugin

    plugin = VoiceSupportPlugin()
    await plugin.initialize(config={})
    ctx = _MockCtx()
    await plugin.setup(ctx)

    assert provider_name in _registered_names(ctx)


@pytest.mark.asyncio
async def test_openai_registers_when_sdk_and_key_present(monkeypatch):
    pytest.importorskip("openai")
    _clear_credentials(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from voice_support import VoiceSupportPlugin

    plugin = VoiceSupportPlugin()
    await plugin.initialize(config={})
    ctx = _MockCtx()
    await plugin.setup(ctx)

    assert "openai" in _registered_names(ctx)
