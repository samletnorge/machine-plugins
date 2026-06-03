# voice_support

Framework plugin for voice-provider abstractions and voice-agent helpers.

## Provides

- the `voice_provider` registry category
- shared config and request types for speaking, listening, and realtime connections
- a `VoiceProvider` abstraction and realtime session types
- `VoiceAgentPipeline` for wiring speech input through an agent and back to synthesized output

## Key Files

- `manifest.json`
- `voice_support/__init__.py`
- `voice_support/base.py`
- `voice_support/pipeline.py`
- `voice_support/utils.py`

## Role

This plugin defines the common interface for speech and realtime voice integrations across Machine runtimes.
