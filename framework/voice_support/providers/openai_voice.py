"""OpenAI voice provider (TTS + STT + Realtime)."""

from __future__ import annotations

import io
import tempfile
from typing import AsyncIterator

from ..base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    RealtimeSession,
)

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment,misc]

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]


class _OpenAIRealtimeSession:
    def __init__(self, ws):
        self._ws = ws

    async def send(self, audio: bytes) -> None:
        await self._ws.send(audio)

    async def receive(self) -> bytes | str:
        return await self._ws.recv()

    async def close(self) -> None:
        await self._ws.close()


class OpenAIVoiceProvider(VoiceProvider):
    def __init__(self, api_key: str, model: str = "tts-1"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._api_key = api_key

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        opts = options or SpeakOptions()
        voice = opts.voice or "alloy"
        fmt_map = {
            "pcm": "pcm",
            "mp3": "mp3",
            "wav": "wav",
            "ogg": "opus",
            "flac": "flac",
        }
        response_format = fmt_map.get(opts.format.value, "pcm")

        response = await self._client.audio.speech.create(
            model=self._model,
            voice=voice,
            input=text,
            speed=opts.speed,
            response_format=response_format,
        )

        async def _iter():
            for chunk in response.iter_bytes():
                yield chunk

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        chunks = []
        async for chunk in audio:
            chunks.append(chunk)
        audio_data = b"".join(chunks)

        kwargs: dict = {
            "model": "whisper-1",
            "file": ("audio.wav", io.BytesIO(audio_data)),
        }
        if options and options.language:
            kwargs["language"] = options.language

        result = await self._client.audio.transcriptions.create(**kwargs)
        return result.text

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        ws = await websockets.connect(
            "wss://api.openai.com/v1/realtime",
            additional_headers={"Authorization": f"Bearer {self._api_key}"},
        )
        return _OpenAIRealtimeSession(ws)
