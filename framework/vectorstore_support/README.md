# vectorstore_support

Framework plugin that defines the shared `vector_store` category.

## Provides

- the `vector_store` registry category
- common operations such as `upsert`, `search`, `delete`, and `list`
- request and response schemas for indexing and retrieval
- hook points around search and upsert behavior

## Key Files

- `manifest.json`
- `vectorstore_support/__init__.py`
- `vectorstore_support/schemas.py`
- `vectorstore_support/hooks.py`

## Role

This plugin supplies the shared contract used by concrete vector store implementations.
