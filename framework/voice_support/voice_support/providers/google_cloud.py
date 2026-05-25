"""Google Cloud TTS/STT provider."""

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
    from google.cloud import texttospeech, speech
except ImportError:
    texttospeech = None  # type: ignore[assignment]
    speech = None  # type: ignore[assignment]


class GoogleCloudVoiceProvider(VoiceProvider):
    def __init__(self, voice: str | None = None, language_code: str = "en-US"):
        self._tts_client = texttospeech.TextToSpeechClient()
        self._stt_client = speech.SpeechClient()
        self._voice = voice
        self._language_code = language_code

    async def speak(
        self, text: str, options: SpeakOptions | None = None
    ) -> AsyncIterator[bytes]:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=self._language_code,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )
        response = self._tts_client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )

        async def _iter():
            yield response.audio_content

        return _iter()

    async def listen(
        self, audio: AsyncIterator[bytes], options: ListenOptions | None = None
    ) -> str:
        chunks = []
        async for chunk in audio:
            chunks.append(chunk)
        audio_data = b"".join(chunks)

        lang = self._language_code
        if options and options.language:
            lang = options.language

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=lang,
        )
        audio_obj = speech.RecognitionAudio(content=audio_data)
        response = self._stt_client.recognize(config=config, audio=audio_obj)
        return response.results[0].alternatives[0].transcript

    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession:
        raise NotImplementedError("GoogleCloudVoiceProvider does not support realtime")
