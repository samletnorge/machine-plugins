"""Fish Audio TTS provider."""

from __future__ import annotations

import json
from typing import AsyncIterator

from ..base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    RealtimeSession,
)

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


class FishAudioProvider(VoiceProvider):
    def __init__(self, api_key: str, reference_id: str | None = None):
        self._api_key = api_key
        self._reference_id = reference_id

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        payload = {"text": text}
        if self._reference_id:
            payload["reference_id"] = self._reference_id

        async def _iter():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.fish.audio/v1/tts",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        raise NotImplementedError("FishAudioProvider is TTS-only")

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("FishAudioProvider does not support realtime")
