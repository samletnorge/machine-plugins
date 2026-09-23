# Voice

`voice_support` defines the `voice_provider` category, the `VoiceProvider` abstraction, and a
`VoiceAgentPipeline` that wires speech-to-text → agent → text-to-speech. Provider
implementations (Edge TTS, gTTS, OpenAI, ElevenLabs, Deepgram, Azure, Google Cloud, Fish
Audio, Whisper) ship in the same package.

## Enable it

```toml
plugins = ["voice_support", "agent_support", "..."]
```

## The contract

```python
class VoiceProvider(ABC):
    async def speak(self, text: str, options: SpeakOptions | None = None) -> AsyncIterator[bytes]: ...
    async def listen(self, audio: AsyncIterator[bytes], options: ListenOptions | None = None) -> str: ...
    async def connect(self, options: ConnectOptions | None = None) -> RealtimeSession: ...
```

Supporting types: `AudioFormat`, `SpeakOptions`, `ListenOptions`, `ConnectOptions`,
`VoiceConfig`, and a `RealtimeSession` protocol (`send`, `receive`, `close`).

The category declares operations `speak` (POST), `listen` (POST), `connect` (POST), and
`list` (GET).

## Available providers

| Module | Provider | Notes |
|--------|----------|-------|
| `voice_support.providers.edge_tts` | `EdgeTTSProvider(voice="en-US-GuyNeural")` | Free, no API key. |
| `voice_support.providers.gtts` | `GTTSProvider(language="en")` | Free, no API key. |
| `voice_support.providers.openai_voice` | `OpenAIVoiceProvider(api_key, model="tts-1")` | Includes realtime session. |
| `voice_support.providers.elevenlabs` | `ElevenLabsProvider(api_key, voice="Rachel")` | |
| `voice_support.providers.deepgram` | `DeepgramProvider(api_key)` | |
| `voice_support.providers.azure` | `AzureVoiceProvider(...)` | |
| `voice_support.providers.google_cloud` | `GoogleCloudVoiceProvider(voice=None, language_code="en-US")` | |
| `voice_support.providers.fish_audio` | `FishAudioProvider(api_key, reference_id=None)` | |
| `voice_support.providers.whisper_local` | `WhisperLocalProvider(model_size="base")` | Local STT. |

> **Note:** `voice_support` registers only the `voice_provider` **category** in its `setup()`.
> The provider classes are not auto-registered. Register the one you want from your project
> (or a thin wrapper plugin) so `machine.resolve("voice_provider", ...)` finds it.

```python
from voice_support.providers.edge_tts import EdgeTTSProvider

@machine.when_ready
async def _register_voice():
    machine.register("voice_provider", "edge", EdgeTTSProvider())
```

## The voice-to-agent pipeline

`VoiceAgentPipeline` runs the full loop:

```python
import asyncio
from voice_support.pipeline import VoiceAgentPipeline
from voice_support.providers.edge_tts import EdgeTTSProvider
from voice_support.providers.whisper_local import WhisperLocalProvider

pipeline = VoiceAgentPipeline(
    agent=agent,                              # anything with async run(text)
    stt_provider=WhisperLocalProvider(),
    tts_provider=EdgeTTSProvider(),
)
```

- `run(audio_input)` is an async generator: yields synthesized audio chunks.
- `run_with_transcript(audio_input)` returns a `PipelineResult` with `user_text`,
  `agent_text`, and `audio_chunks`.

```python
async def stream_audio():
    yield b"..."   # PCM/WAV bytes

async for chunk in pipeline.run(stream_audio()):
    play(chunk)
```

```python
result = await pipeline.run_with_transcript(stream_audio())
print(result.user_text, "->", result.agent_text)
```

Pass one `voice_provider` (used for both STT and TTS) or separate `stt_provider` and
`tts_provider` — the constructor raises `ValueError` if you provide neither.

## Audio helpers

`voice_support.utils` includes `create_wav_header`, `pcm_to_wav`, `chunk_audio`, and
`detect_audio_format` for working with raw audio streams.

## HTTP

With `server_support`, a registered voice provider exposes:

```
GET  /api/voice_provider
POST /api/voice_provider/{name}/speak
POST /api/voice_provider/{name}/listen
POST /api/voice_provider/{name}/connect
```

Studio also renders a Voice domain under `/_studio/` (see [Studio](studio.md#domains)).

## Tips

- Use `edge_tts` or `gtts` for a zero-key local demo.
- Use `whisper_local` for local STT and a hosted provider for higher quality.
- Keep audio framing consistent: `detect_audio_format` and `pcm_to_wav` help normalize it.

---

**Read next:** [Browser](browser.md) · [Workspaces](workspaces.md)

**Source:** `framework/voice_support/`.
