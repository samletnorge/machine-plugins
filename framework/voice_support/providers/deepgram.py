"""Deepgram STT provider."""

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
    from deepgram import DeepgramClient, PrerecordedOptions
except ImportError:
    DeepgramClient = None  # type: ignore[assignment,misc]
    PrerecordedOptions = None  # type: ignore[assignment,misc]


class DeepgramProvider(VoiceProvider):
    def __init__(self, api_key: str):
        self._client = DeepgramClient(api_key)

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        raise NotImplementedError("DeepgramProvider is STT-only")

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        chunks = []
        async for chunk in audio:
            chunks.append(chunk)
        audio_data = b"".join(chunks)

        opts = PrerecordedOptions(model="nova-2", smart_format=True)
        if options and options.language:
            opts.language = options.language

        response = await self._client.listen.asyncrest.v1.transcribe_file(
            {"buffer": audio_data}, opts
        )
        return response.results.channels[0].alternatives[0].transcript

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("DeepgramProvider does not support realtime")
