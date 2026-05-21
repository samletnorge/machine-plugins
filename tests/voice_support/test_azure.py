"""Tests for Azure Cognitive Services TTS/STT provider."""

import pytest
from unittest.mock import MagicMock, patch
from machine_core.plugins.voice_support.base import SpeakOptions, ListenOptions


class TestAzureVoiceProvider:
    def test_import(self):
        with patch("machine_core.plugins.voice_support.providers.azure.speechsdk"):
            from machine_core.plugins.voice_support.providers.azure import (
                AzureVoiceProvider,
            )

            provider = AzureVoiceProvider(subscription_key="test-key", region="eastus")
            assert provider is not None

    @pytest.mark.asyncio
    async def test_speak_returns_chunks(self):
        with patch(
            "machine_core.plugins.voice_support.providers.azure.speechsdk"
        ) as mock_sdk:
            from machine_core.plugins.voice_support.providers.azure import (
                AzureVoiceProvider,
            )

            mock_result = MagicMock()
            mock_result.audio_data = b"\x00" * 500
            mock_result.reason = mock_sdk.ResultReason.SynthesizingAudioCompleted

            mock_synthesizer = MagicMock()
            mock_synthesizer.speak_text_async.return_value.get.return_value = (
                mock_result
            )
            mock_sdk.SpeechSynthesizer.return_value = mock_synthesizer

            provider = AzureVoiceProvider(subscription_key="test-key", region="eastus")
            chunks = []
            async for chunk in await provider.speak("Hello"):
                chunks.append(chunk)
            assert b"".join(chunks) == b"\x00" * 500

    @pytest.mark.asyncio
    async def test_listen_returns_text(self):
        with patch(
            "machine_core.plugins.voice_support.providers.azure.speechsdk"
        ) as mock_sdk:
            from machine_core.plugins.voice_support.providers.azure import (
                AzureVoiceProvider,
            )

            mock_result = MagicMock()
            mock_result.text = "Hello world"
            mock_result.reason = mock_sdk.ResultReason.RecognizedSpeech

            mock_recognizer = MagicMock()
            mock_recognizer.recognize_once_async.return_value.get.return_value = (
                mock_result
            )
            mock_sdk.SpeechRecognizer.return_value = mock_recognizer

            provider = AzureVoiceProvider(subscription_key="test-key", region="eastus")

            async def audio_gen():
                yield b"\x00" * 100

            result = await provider.listen(audio_gen())
            assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_connect_raises(self):
        with patch("machine_core.plugins.voice_support.providers.azure.speechsdk"):
            from machine_core.plugins.voice_support.providers.azure import (
                AzureVoiceProvider,
            )

            provider = AzureVoiceProvider(subscription_key="test-key", region="eastus")
            with pytest.raises(NotImplementedError):
                await provider.connect()
