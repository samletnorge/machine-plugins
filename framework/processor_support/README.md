# processor_support

Framework plugin for middleware-style processor pipelines.

## Provides

- the `processor` registry category
- processor pipeline contracts such as `Processor`, `ProcessorData`, `TripWire`, and `ProcessorRunner`
- built-in processors for PII detection, prompt injection checks, token limiting, cost guarding, regex filtering, and caching

## Key Files

- `manifest.json`
- `machine_processor/__init__.py`
- `machine_processor/base.py`
- `machine_processor/runner.py`

## Role

This plugin supplies a common pre/post-processing pipeline for agent or model flows that need safety, policy, caching, or request shaping.
