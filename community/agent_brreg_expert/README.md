# agent_brreg_expert

Domain plugin that composes Brreg data, OpenAPI-generated tools, RAG, and an agent runtime.

## Provides

- a Brreg-focused `rag_pipeline`
- a Brreg-focused `agent`
- bulk ingest of Brønnøysundregistrene data
- live OpenAPI-derived Brreg tools
- semantic tool filtering before agent execution

## Key Files

- `manifest.json`
- `__init__.py`
- `runner.py`
- `pipeline.py`
- `ingestor.py`
- `merger.py`

## Role

This plugin is an example of domain composition on top of the broader Machine plugin graph. It combines data ingest, retrieval, tool generation, tool filtering, and a standard agent runtime into a single domain expert.
