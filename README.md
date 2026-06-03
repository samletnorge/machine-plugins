# machine-plugins

Framework and community plugin catalog for `machine-core`.

## Overview

`machine-core` provides the generic runtime kernel: registry, plugin lifecycle, hooks, events, config resolution, and transport. `machine-plugins` is where most application-facing behavior lives.

This repository contains two kinds of plugins:

- `framework/`: plugins that define shared categories, contracts, hook specs, and support packages
- `community/`: plugins that register concrete implementations, runtimes, integrations, and domain behavior

Projects typically compose a runtime by listing plugins under `[tool.machine-core].plugins` in `pyproject.toml`.

## Repository Layout

- `framework/`: category-defining and support plugins
- `community/`: concrete providers, runtimes, RAG helpers, deployers, workspace tools, and domain plugins
- `manifests/`: standalone manifests for plugins packaged elsewhere
- `tests/`: integration and behavior tests across the plugin ecosystem

## Framework Plugins

Framework plugins define the vocabulary of the system.

- `agent_support`: `agent` category, agent schemas, lifecycle hooks
- `tool_support`: `tool` category, tool schemas, `@tool` decorator
- `model_provider_support`: `model_provider` category and request/response contracts
- `embeddings`: `embedding` category and embedding contracts
- `vectorstore_support`: `vector_store` category and vector-store contracts
- `workflow_support`: workflow orchestration categories and execution-engine contracts
- `memory_support`: memory and storage-backend contracts
- `voice_support`: voice-provider abstractions and pipeline helpers
- `server_support`: FastAPI app generation from a `Machine` registry
- `studio_support`: Studio web UI and runtime attachment helpers

These plugins usually do not contain end-user behavior by themselves. They establish categories and contracts that implementation plugins can target.

## Community Plugins

Community plugins provide actual implementations and integrations.

Examples in this repository include:

- model providers such as `provider_ollama`, `provider_groq`, `provider_google_gemini`, and Vertex/Azure variants
- embedding providers such as `embeddings_ollama`, `embeddings_google`, `embeddings_azure`, and `embeddings_sentence_transformers`
- agent runtimes such as `agent_runtime_basic` and `agent_runtime_pydantic`
- retrieval and tooling helpers such as `rag_support`, `tool_openapi`, and `tool_filter_rag`
- infrastructure plugins such as `browser_support`, `deployer_support`, `workspace_support`, `pubsub_support`, and `observability_support`
- domain composition plugins such as `agent_brreg_expert`

## Plugin Model

Each plugin is described by a `manifest.json` and typically exposes a plugin class with `initialize()`, `setup(ctx)`, and `shutdown()` methods.

Typical lifecycle:

1. `machine-core` discovers or loads the manifest
2. config is resolved centrally
3. the plugin is initialized with the resolved config
4. `setup(ctx)` is called with a capability-scoped `PluginContext`
5. the plugin defines categories, registers implementations, or subscribes to hooks and events

Plugins collaborate primarily through the registry:

- `ctx.register_category(...)`
- `ctx.register(...)`
- `machine.resolve(category, name)`
- `machine.list_category(category)`

## Capability Model

`PluginContext` is intentionally capability-gated.

Common capabilities include:

- `categories:define`
- `hooks:define`
- `hooks:subscribe`
- `events:emit`
- `events:subscribe`
- category-specific registration capabilities such as `agent:register`, `tool:register`, or `model_provider:register`
- `data:own` for plugin-owned runtime state

The manifest is the primary contract between the plugin and `machine-core`.

## Transport Options

Plugins can run:

- in-process through Python import
- out-of-process through JSON-RPC with spawned subprocesses
- out-of-process through JSON-RPC by connecting to an already-running process

That is what makes the overall plugin architecture language-agnostic.

## Relationship To Projects

A project can stay very small. In many cases it only needs:

- a `pyproject.toml` with `[tool.machine-core]`
- a plugin list
- optional per-plugin config overrides
- a small bootstrap such as `Machine(config=MachineConfig.from_pyproject())`

The selected plugins collectively define the runtime behavior.

## Read Next

- `registry.json`
- `framework/agent_support/README.md`
- `framework/tool_support/README.md`
- `framework/server_support/README.md`
- `community/agent_runtime_basic/README.md`
- `community/provider_ollama/README.md`
- `community/rag_support/README.md`
