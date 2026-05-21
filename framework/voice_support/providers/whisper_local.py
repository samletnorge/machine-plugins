"""Local Whisper STT provider."""

from __future__ import annotations

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
    import whisper
except ImportError:
    whisper = None  # type: ignore[assignment]


class WhisperLocalProvider(VoiceProvider):
    def __init__(self, model_size: str = "base"):
        self._model = whisper.load_model(model_size)

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        raise NotImplementedError("WhisperLocalProvider is STT-only")

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        chunks = []
        async for chunk in audio:
            chunks.append(chunk)
        audio_data = b"".join(chunks)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_data)
            f.flush()
            kwargs: dict = {"fp16": False}
            if options and options.language:
                kwargs["language"] = options.language
            result = self._model.transcribe(f.name, **kwargs)

        return result["text"]

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("WhisperLocalProvider does not support realtime")
