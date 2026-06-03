# tool_filter_rag

Semantic tool-selection helper for Machine.

## Provides

- an internal tool-registry utility named `tool/__filter_rag__`
- embedding of tool descriptions into a vector store
- semantic retrieval of relevant tools for a prompt

## Key Files

- `manifest.json`
- `__init__.py`
- `filter.py`

## Role

This plugin helps larger tool graphs stay usable by narrowing the active tool set based on semantic similarity.
