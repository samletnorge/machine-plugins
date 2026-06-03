# storage_support

Framework plugin that adds concrete storage backends to the shared storage contract.

## Provides

- implementations for the `storage-backend` category defined by `memory_support`
- shared storage models such as `StorageBackend`, `StorageBucket`, and `StorageObject`
- built-in `local` and `s3`-style storage backends

## Key Files

- `manifest.json`
- `machine_storage/__init__.py`

## Role

This plugin supplies concrete storage backends that other memory or file-oriented features can reuse.
