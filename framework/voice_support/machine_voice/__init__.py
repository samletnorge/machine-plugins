"""Voice support plugin — defines voice_provider category and houses all voice providers."""

from machine_core.plugins.voice_support.base import (
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


class VoiceSupportPlugin:
    """Plugin that defines the voice_provider category."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

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

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
