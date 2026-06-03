# embeddings

Framework plugin that defines the shared `embedding` category.

## Provides

- the `embedding` registry category
- embedding operations such as `embed` and `list`
- shared request and response models including `EmbeddingRequest` and `EmbeddingResult`
- embedding lifecycle hooks such as `before_embed` and `after_embed`

## Key Files

- `manifest.json`
- `embeddings/__init__.py`
- `embeddings/schemas.py`
- `embeddings/hooks.py`

## Role

This plugin establishes the contract used by embedding provider plugins throughout the Machine ecosystem.
