"""Voice support plugin — defines voice_provider category and houses all voice providers."""

from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

from voice_support.base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    RealtimeSession,
    AudioFormat,
    VoiceConfig,
)

__all__ = [
    "VoiceSupportPlugin",
    "VoiceProvider",
    "SpeakOptions",
    "ListenOptions",
    "ConnectOptions",
    "RealtimeSession",
    "AudioFormat",
    "VoiceConfig",
]


def _lookup(config: dict, keys: tuple[str, ...], env: str | None = None):
    """Resolve a value from plugin config first, then environment."""
    for key in keys:
        value = config.get(key)
        if value:
            return value
    if env:
        value = os.environ.get(env)
        if value:
            return value
    return None


# Declarative description of the shipped providers. A provider is registered
# only when its SDK is importable AND its credentials resolve. The constructors
# are the same ones exercised by the unit tests, so no extra indirection.
_PROVIDER_SPECS: list[dict] = [
    {
        "name": "openai",
        "sdk": "openai",
        "module": "voice_support.providers.openai_voice",
        "attr": "OpenAIVoiceProvider",
        "available": lambda c: bool(
            _lookup(c, ("openai_api_key", "api_key"), "OPENAI_API_KEY")
        ),
        "kwargs": lambda c: {
            "api_key": _lookup(c, ("openai_api_key", "api_key"), "OPENAI_API_KEY")
        },
    },
    {
        "name": "azure",
        "sdk": "azure.cognitiveservices.speech",
        "module": "voice_support.providers.azure",
        "attr": "AzureVoiceProvider",
        "available": lambda c: bool(
            _lookup(c, ("azure_speech_key", "subscription_key"), "AZURE_SPEECH_KEY")
        )
        and bool(
            _lookup(
                c, ("azure_speech_region", "region"), "AZURE_SPEECH_REGION"
            )
        ),
        "kwargs": lambda c: {
            "subscription_key": _lookup(
                c, ("azure_speech_key", "subscription_key"), "AZURE_SPEECH_KEY"
            ),
            "region": _lookup(
                c, ("azure_speech_region", "region"), "AZURE_SPEECH_REGION"
            ),
        },
    },
    {
        "name": "google_cloud",
        "sdk": "google.cloud.texttospeech",
        "module": "voice_support.providers.google_cloud",
        "attr": "GoogleCloudVoiceProvider",
        "available": lambda c: bool(
            _lookup(
                c,
                ("google_application_credentials",),
                "GOOGLE_APPLICATION_CREDENTIALS",
            )
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        ),
        "kwargs": lambda c: {"language_code": c.get("google_language_code", "en-US")},
    },
    {
        "name": "fish_audio",
        "sdk": "httpx",
        "module": "voice_support.providers.fish_audio",
        "attr": "FishAudioProvider",
        "available": lambda c: bool(
            _lookup(c, ("fish_audio_api_key", "api_key"), "FISH_AUDIO_API_KEY")
        ),
        "kwargs": lambda c: {
            "api_key": _lookup(
                c, ("fish_audio_api_key", "api_key"), "FISH_AUDIO_API_KEY"
            ),
            "reference_id": c.get("fish_audio_reference_id"),
        },
    },
    {
        "name": "edge_tts",
        "sdk": "edge_tts",
        "module": "voice_support.providers.edge_tts",
        "attr": "EdgeTTSProvider",
        "available": lambda c: True,
        "kwargs": lambda c: {"voice": c.get("edge_tts_voice", "en-US-GuyNeural")},
    },
    {
        "name": "whisper_local",
        "sdk": "whisper",
        "module": "voice_support.providers.whisper_local",
        "attr": "WhisperLocalProvider",
        "available": lambda c: True,
        "kwargs": lambda c: {"model_size": c.get("whisper_model", "base")},
    },
    {
        "name": "deepgram",
        "sdk": "deepgram",
        "module": "voice_support.providers.deepgram",
        "attr": "DeepgramProvider",
        "available": lambda c: bool(
            _lookup(c, ("deepgram_api_key", "api_key"), "DEEPGRAM_API_KEY")
        ),
        "kwargs": lambda c: {
            "api_key": _lookup(c, ("deepgram_api_key", "api_key"), "DEEPGRAM_API_KEY")
        },
    },
    {
        "name": "elevenlabs",
        "sdk": "elevenlabs",
        "module": "voice_support.providers.elevenlabs",
        "attr": "ElevenLabsProvider",
        "available": lambda c: bool(
            _lookup(c, ("elevenlabs_api_key", "api_key"), "ELEVENLABS_API_KEY")
        ),
        "kwargs": lambda c: {
            "api_key": _lookup(
                c, ("elevenlabs_api_key", "api_key"), "ELEVENLABS_API_KEY"
            ),
            "voice": c.get("elevenlabs_voice", "Rachel"),
        },
    },
    {
        "name": "gtts",
        "sdk": "gtts",
        "module": "voice_support.providers.gtts",
        "attr": "GTTSProvider",
        "available": lambda c: True,
        "kwargs": lambda c: {"language": c.get("gtts_language", "en")},
    },
]


class VoiceSupportPlugin:
    """Plugin that defines the voice_provider category."""

    def __init__(self) -> None:
        self._config: dict = {}

    async def initialize(self, config=None, **kwargs):
        """Store plugin config; setup performs the actual registration."""
        self._config = config or {}

    async def setup(self, ctx):
        ctx.register_category(
            "voice_provider",
            operations={
                "speak": {"method": "POST", "on": "item"},
                "listen": {"method": "POST", "on": "item"},
                "connect": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        self._register_providers(ctx)

    def _register_providers(self, ctx) -> None:
        """Conditionally register each shipped provider.

        A missing SDK or missing credentials is a normal condition and must
        never break plugin setup — each provider is isolated in try/except.
        """
        for spec in _PROVIDER_SPECS:
            name = spec["name"]

            try:
                importlib.import_module(spec["sdk"])
            except Exception as exc:
                logger.debug(
                    "voice_support: skipping '{}' — SDK '{}' unavailable ({})",
                    name,
                    spec["sdk"],
                    exc,
                )
                continue

            try:
                if not spec["available"](self._config):
                    logger.debug(
                        "voice_support: skipping '{}' — required credentials "
                        "not configured",
                        name,
                    )
                    continue

                module = importlib.import_module(spec["module"])
                provider_cls = getattr(module, spec["attr"])
                provider = provider_cls(**spec["kwargs"](self._config))
            except Exception as exc:
                logger.debug(
                    "voice_support: skipping '{}' — initialization failed ({})",
                    name,
                    exc,
                )
                continue

            ctx.register("voice_provider", name, provider)

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
