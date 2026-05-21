"""Edge TTS provider (free, no API key needed)."""

from __future__ import annotations

from typing import AsyncIterator

from ..base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    RealtimeSession,
)

try:
    import edge_tts
except ImportError:
    edge_tts = None  # type: ignore[assignment]


class EdgeTTSProvider(VoiceProvider):
    def __init__(self, voice: str = "en-US-GuyNeural"):
        self.voice = voice

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        voice = self.voice
        if options and options.voice:
            voice = options.voice

        rate = "+0%"
        if options and options.speed != 1.0:
            pct = int((options.speed - 1.0) * 100)
            rate = f"{pct:+d}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)

        async def _iter():
            async for item in communicate.stream():
                if item["type"] == "audio":
                    yield item["data"]

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        raise NotImplementedError("EdgeTTSProvider is TTS-only")

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("EdgeTTSProvider does not support realtime")
