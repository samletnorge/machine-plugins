# prompt_support

Framework plugin for reusable prompt templates and prompt composition.

## Provides

- the `prompt` registry category
- prompt schemas such as `PromptTemplate`, `PromptVariable`, `PromptBlock`, and `RenderedPrompt`
- a prompt registry with registration, retrieval, rendering, and composition helpers
- hook points before and after prompt rendering

## Key Files

- `manifest.json`
- `prompt_support/__init__.py`
- `prompt_support/schemas.py`
- `prompt_support/registry.py`

## Role

This plugin defines the prompt-layer contract for Machine projects that want versioned templates and reusable rendering behavior.
