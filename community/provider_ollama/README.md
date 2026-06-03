# provider_ollama

Reference Ollama model provider for Machine.

## Provides

- the `model_provider/ollama` implementation
- direct Ollama chat and streaming calls over `httpx`
- a pydantic-ai compatible model for runtimes that need it

## Key Files

- `manifest.json`
- `__init__.py`
- `provider.py`

## Role

This plugin is a reference model provider that shows how to implement the shared `model_provider` contract with both direct runtime behavior and pydantic-ai compatibility.
