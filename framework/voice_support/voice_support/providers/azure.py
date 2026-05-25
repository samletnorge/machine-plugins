"""Azure Cognitive Services TTS/STT provider."""

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
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None  # type: ignore[assignment]


class AzureVoiceProvider(VoiceProvider):
    def __init__(
        self, subscription_key: str, region: str, voice: str = "en-US-JennyNeural"
    ):
        self._subscription_key = subscription_key
        self._region = region
        self._voice = voice

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        config = speechsdk.SpeechConfig(
            subscription=self._subscription_key, region=self._region
        )
        voice = self._voice
        if options and options.voice:
            voice = options.voice
        config.speech_synthesis_voice_name = voice

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config, audio_config=None
        )
        result = synthesizer.speak_text_async(text).get()

        async def _iter():
            yield result.audio_data

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        chunks = []
        async for chunk in audio:
            chunks.append(chunk)
        audio_data = b"".join(chunks)

        config = speechsdk.SpeechConfig(
            subscription=self._subscription_key, region=self._region
        )
        if options and options.language:
            config.speech_recognition_language = options.language

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_data)
            f.flush()
            audio_cfg = speechsdk.AudioConfig(filename=f.name)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=config, audio_config=audio_cfg
            )
            result = recognizer.recognize_once_async().get()

        return result.text

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("AzureVoiceProvider does not support realtime")
