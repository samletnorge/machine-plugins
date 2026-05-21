"""Tests for voice-to-agent pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from machine_core.plugins.voice_support.pipeline import VoiceAgentPipeline
from machine_core.plugins.voice_support.base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
)


class MockSTTProvider(VoiceProvider):
    """Mock STT-only provider."""

    async def speak(self, text, options=None):
        raise NotImplementedError

    async def listen(self, audio, options=None):
        return "What is the weather?"

    async def connect(self, options=None):
        raise NotImplementedError


class MockTTSProvider(VoiceProvider):
    """Mock TTS-only provider."""

    async def speak(self, text, options=None):
        async def _gen():
            yield f"audio:{text}".encode()

        return _gen()

    async def listen(self, audio, options=None):
        raise NotImplementedError

    async def connect(self, options=None):
        raise NotImplementedError


class MockFullProvider(VoiceProvider):
    """Mock provider that supports both TTS and STT."""

    async def speak(self, text, options=None):
        async def _gen():
            yield f"audio:{text}".encode()

        return _gen()

    async def listen(self, audio, options=None):
        return "Transcribed text"

    async def connect(self, options=None):
        raise NotImplementedError


class MockAgent:
    """Mock agent."""

    def __init__(self, response: str = "The weather is sunny."):
        self._response = response
        self.name = "test_agent"

    async def run(self, prompt: str, **kwargs):
        result = MagicMock()
        result.output = self._response
        result.data = self._response
        return result


class TestVoiceAgentPipeline:
    def test_create_with_separate_providers(self):
        stt = MockSTTProvider()
        tts = MockTTSProvider()
        agent = MockAgent()
        pipeline = VoiceAgentPipeline(agent=agent, stt_provider=stt, tts_provider=tts)
        assert pipeline is not None

    def test_create_with_single_provider(self):
        provider = MockFullProvider()
        agent = MockAgent()
        pipeline = VoiceAgentPipeline(agent=agent, voice_provider=provider)
        assert pipeline is not None

    @pytest.mark.asyncio
    async def test_process_audio_to_audio(self):
        stt = MockSTTProvider()
        tts = MockTTSProvider()
        agent = MockAgent("It's sunny today.")
        pipeline = VoiceAgentPipeline(agent=agent, stt_provider=stt, tts_provider=tts)

        async def audio_input():
            yield b"\x00" * 100

        chunks = []
        async for chunk in pipeline.run(audio_input()):
            chunks.append(chunk)

        assert len(chunks) >= 1
        assert b"sunny" in b"".join(chunks)

    @pytest.mark.asyncio
    async def test_process_returns_text_transcript(self):
        stt = MockSTTProvider()
        tts = MockTTSProvider()
        agent = MockAgent("Response text.")
        pipeline = VoiceAgentPipeline(agent=agent, stt_provider=stt, tts_provider=tts)

        async def audio_input():
            yield b"\x00" * 100

        result = await pipeline.run_with_transcript(audio_input())
        assert result.user_text == "What is the weather?"
        assert result.agent_text == "Response text."
        assert len(result.audio_chunks) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_with_single_provider(self):
        provider = MockFullProvider()
        agent = MockAgent("Agent response.")
        pipeline = VoiceAgentPipeline(agent=agent, voice_provider=provider)

        async def audio_input():
            yield b"\x00" * 100

        chunks = []
        async for chunk in pipeline.run(audio_input()):
            chunks.append(chunk)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_raises_without_providers(self):
        agent = MockAgent()
        with pytest.raises(ValueError, match="provider"):
            VoiceAgentPipeline(agent=agent)
