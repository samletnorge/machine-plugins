# memory_support

Framework plugin for thread-based memory and storage contracts.

## Provides

- the `memory` and `storage-backend` registry categories
- memory operations such as thread creation, listing, retrieval, message append, and delete
- shared thread, message, fact, and storage abstractions
- working-memory, observational-memory, and windowing utilities
- a `MemoryManager` that coordinates memory behavior

## Key Files

- `manifest.json`
- `memory_support/__init__.py`
- `memory_support/thread.py`
- `memory_support/storage.py`
- `memory_support/manager.py`
- `memory_support/working.py`
- `memory_support/observational.py`
- `memory_support/windowing.py`

## Role

This plugin defines the core memory vocabulary used by storage backends and higher-level agent or workflow systems.
