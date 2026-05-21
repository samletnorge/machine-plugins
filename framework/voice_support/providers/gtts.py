"""Google Translate TTS provider."""

from __future__ import annotations

import io
from typing import AsyncIterator

from ..base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
    ConnectOptions,
    RealtimeSession,
)

try:
    from gtts import gTTS
except ImportError:
    gTTS = None  # type: ignore[assignment,misc]


class GTTSProvider(VoiceProvider):
    def __init__(self, language: str = "en"):
        self._language = language

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        lang = self._language
        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        audio_data = buf.getvalue()

        async def _iter():
            yield audio_data

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        raise NotImplementedError("GTTSProvider is TTS-only")

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("GTTSProvider does not support realtime")
