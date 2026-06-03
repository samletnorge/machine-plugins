# model_provider_support

Framework plugin that defines the shared `model_provider` category.

## Provides

- the `model_provider` registry category
- common operations such as `generate`, `stream`, and `list`
- shared request, response, and config models for model providers
- hook points around model invocation and errors

## Key Files

- `manifest.json`
- `model_provider_support/__init__.py`
- `model_provider_support/schemas.py`
- `model_provider_support/hooks.py`

## Role

This plugin establishes the common contract that concrete model-provider plugins implement, regardless of backend.
