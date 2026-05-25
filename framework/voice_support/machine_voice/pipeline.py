"""Voice-to-agent pipeline: audio -> STT -> agent.run() -> TTS -> audio."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator

from voice_support.base import (
    VoiceProvider,
    SpeakOptions,
    ListenOptions,
)


@dataclass
class PipelineResult:
    user_text: str
    agent_text: str
    audio_chunks: list[bytes] = field(default_factory=list)


class VoiceAgentPipeline:
    def __init__(
        self,
        agent,
        voice_provider: VoiceProvider | None = None,
        stt_provider: VoiceProvider | None = None,
        tts_provider: VoiceProvider | None = None,
        speak_options: SpeakOptions | None = None,
        listen_options: ListenOptions | None = None,
    ):
        self.agent = agent
        if voice_provider:
            self._stt = voice_provider
            self._tts = voice_provider
        elif stt_provider and tts_provider:
            self._stt = stt_provider
            self._tts = tts_provider
        else:
            raise ValueError(
                "Provide either voice_provider (supports both TTS/STT) "
                "or both stt_provider and tts_provider."
            )
        self.speak_options = speak_options
        self.listen_options = listen_options

    async def run(self, audio_input: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        user_text = await self._stt.listen(audio_input, self.listen_options)
        result = await self.agent.run(user_text)
        agent_text = result.output if hasattr(result, "output") else result.data
        audio_stream = await self._tts.speak(agent_text, self.speak_options)
        async for chunk in audio_stream:
            yield chunk

    async def run_with_transcript(
        self, audio_input: AsyncIterator[bytes]
    ) -> PipelineResult:
        user_text = await self._stt.listen(audio_input, self.listen_options)
        result = await self.agent.run(user_text)
        agent_text = result.output if hasattr(result, "output") else result.data
        audio_stream = await self._tts.speak(agent_text, self.speak_options)
        audio_chunks = []
        async for chunk in audio_stream:
            audio_chunks.append(chunk)
        return PipelineResult(
            user_text=user_text, agent_text=agent_text, audio_chunks=audio_chunks
        )
