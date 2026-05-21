"""Tests for Google Cloud TTS/STT provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from machine_core.plugins.voice_support.base import SpeakOptions, ListenOptions


class TestGoogleCloudVoiceProvider:
    def test_import(self):
        with patch(
            "machine_core.plugins.voice_support.providers.google_cloud.texttospeech"
        ):
            with patch(
                "machine_core.plugins.voice_support.providers.google_cloud.speech"
            ):
                from machine_core.plugins.voice_support.providers.google_cloud import (
                    GoogleCloudVoiceProvider,
                )

                provider = GoogleCloudVoiceProvider()
                assert provider is not None

    @pytest.mark.asyncio
    async def test_speak_returns_chunks(self):
        with patch(
            "machine_core.plugins.voice_support.providers.google_cloud.texttospeech"
        ) as mock_tts:
            with patch(
                "machine_core.plugins.voice_support.providers.google_cloud.speech"
            ):
                from machine_core.plugins.voice_support.providers.google_cloud import (
                    GoogleCloudVoiceProvider,
                )

                mock_response = MagicMock()
                mock_response.audio_content = b"\x00" * 1000
                mock_tts.TextToSpeechClient.return_value.synthesize_speech.return_value = mock_response

                provider = GoogleCloudVoiceProvider()
                chunks = []
                async for chunk in await provider.speak("Hello"):
                    chunks.append(chunk)
                assert b"".join(chunks) == b"\x00" * 1000

    @pytest.mark.asyncio
    async def test_listen_returns_text(self):
        with patch(
            "machine_core.plugins.voice_support.providers.google_cloud.texttospeech"
        ):
            with patch(
                "machine_core.plugins.voice_support.providers.google_cloud.speech"
            ) as mock_stt:
                from machine_core.plugins.voice_support.providers.google_cloud import (
                    GoogleCloudVoiceProvider,
                )

                mock_result = MagicMock()
                mock_result.results = [MagicMock()]
                mock_result.results[0].alternatives = [MagicMock()]
                mock_result.results[0].alternatives[0].transcript = "Hello world"
                mock_stt.SpeechClient.return_value.recognize.return_value = mock_result

                provider = GoogleCloudVoiceProvider()

                async def audio_gen():
                    yield b"\x00" * 100

                result = await provider.listen(audio_gen())
                assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        with patch(
            "machine_core.plugins.voice_support.providers.google_cloud.texttospeech"
        ):
            with patch(
                "machine_core.plugins.voice_support.providers.google_cloud.speech"
            ):
                from machine_core.plugins.voice_support.providers.google_cloud import (
                    GoogleCloudVoiceProvider,
                )

                provider = GoogleCloudVoiceProvider()
                with pytest.raises(NotImplementedError):
                    await provider.connect()
