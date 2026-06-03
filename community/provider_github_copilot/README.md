# provider_github_copilot

GitHub Copilot model provider for Machine.

## Provides

- the `model_provider/github-copilot` implementation
- device-flow login helpers and cached token handling
- session-token exchange and OpenAI-compatible response patching
- a pydantic-ai compatible model object for runtimes that need one

## Key Files

- `manifest.json`
- `__init__.py`
- `provider.py`
- `auth.py`
- `cli.py`

## Role

This plugin makes GitHub Copilot available through the shared Machine model-provider contract.
