"""ElevenLabs TTS provider."""

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
    from elevenlabs import AsyncElevenLabs
except ImportError:
    AsyncElevenLabs = None  # type: ignore[assignment,misc]


class ElevenLabsProvider(VoiceProvider):
    def __init__(self, api_key: str, voice: str = "Rachel"):
        self._client = AsyncElevenLabs(api_key=api_key)
        self._voice = voice

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        voice = self._voice
        if options and options.voice:
            voice = options.voice

        stream = await self._client.generate(text=text, voice=voice, stream=True)

        async def _iter():
            async for chunk in stream:
                yield chunk

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        raise NotImplementedError("ElevenLabsProvider is TTS-only")

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("ElevenLabsProvider does not support realtime")
