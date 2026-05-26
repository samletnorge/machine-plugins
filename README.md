# machine-plugins

Plugin collection for `machine-core`: framework plugins that define categories and hooks, plus community plugins that register concrete implementations.

## Overview

`machine-core` stays intentionally small. It provides the registry, lifecycle, hook system, event bus, and plugin transport layer. `machine-plugins` is where most real behavior lives.

In practice, a project is assembled by selecting plugins in `pyproject.toml`:

- framework plugins define the shape of the system
- implementation plugins add concrete providers, runtimes, tools, pipelines, storage backends, and integrations
- application projects can stay thin because most behavior is loaded from manifests at startup

## Plugin Model

Each plugin is described by a `manifest.json` and normally exposes a plugin class with `initialize()`, `setup(ctx)`, and `shutdown()`.

Typical lifecycle:

1. `Machine` reads the project's declared plugin list
2. `machine-core` loads each plugin manifest
3. plugin config is resolved from overrides, user config, persisted state, env vars, and defaults
4. the plugin is initialized with the resolved config
5. `setup(ctx)` is called with a capability-scoped `PluginContext`
6. the plugin registers categories, implementations, hooks, or event subscriptions

Plugins do not need hardcoded references to each other. They collaborate through the registry:

- `ctx.register(category, name, impl)` publishes an implementation
- `machine.resolve(category, name)` retrieves one
- `machine.list_category(category)` enumerates available implementations

This makes the system compositional rather than inheritance-heavy.

## Repository Layout

- `framework/`: category-defining plugins and core support plugins
- `community/`: concrete providers, runtimes, RAG helpers, and integrations
- `manifests/`: standalone manifests for plugins packaged elsewhere
- `tests/`: plugin-level behavior and integration tests

## Framework Plugins

Framework plugins define categories, operations, and hook specs. They usually do not provide end-user behavior by themselves.

Common examples:

- `agent_support`: defines the `agent` category
- `tool_support`: defines the `tool` category
- `model_provider_support`: defines the `model_provider` category
- `embeddings`: defines the `embedding` category
- `vectorstore_support`: defines the `vector_store` category
- `workflow_support`: defines workflow-related categories
- `server_support`: defines server hook specs used by the HTTP layer

These plugins establish the vocabulary of the system. Other plugins can then register implementations into those categories.

## Community Plugins

Community plugins provide actual functionality.

Examples:

- `provider_ollama`, `provider_groq`, `provider_google_gemini`: register model providers
- `embeddings_ollama`, `embeddings_google`, `embeddings_azure`: register embedding providers
- `agent_runtime_basic`, `agent_runtime_pydantic`: register agent runtimes
- `tool_openapi`: registers an internal OpenAPI tool generator
- `tool_filter_rag`: registers a semantic tool-filtering utility
- `rag_support`: registers chunkers, rerankers, extractors, and RAG-related categories
- `agent_brreg_expert`: composes tools, RAG, and an agent into a domain-specific expert

Many community plugins are intentionally small. Their job is often just to wire one useful implementation into an existing category.

## Manifest Design

Every plugin has a `manifest.json` with metadata such as:

- `name`, `version`, `description`
- `capabilities`
- `dependencies`
- `config_schema`
- `hooks_subscribed`
- `events_subscribed`
- `transport`

Important fields:

- `capabilities` define what the plugin is allowed to do through `PluginContext`
- `dependencies` document expected upstream plugins in the composition graph
- `config_schema` defines config keys, defaults, env vars, and required fields
- `transport` determines whether the plugin runs in-process or over JSON-RPC

The manifest is the contract between `machine-core` and the plugin.

## Capability Model

`PluginContext` is intentionally restrictive. A plugin cannot do arbitrary registry operations unless it declared the corresponding capability.

Examples:

- `categories:define` allows defining new categories
- `tool:register` allows registering tools
- `agent:register` allows registering agents
- `hooks:define` allows defining hook specs
- `hooks:subscribe` allows subscribing callbacks to hooks
- `events:emit` and `events:subscribe` control event bus access
- `data:own` allows reading and writing the plugin's persisted runtime state

This keeps plugin behavior explicit and auditable from the manifest.

## Configuration Resolution

Plugins do not load their own config files directly. `machine-core` resolves config centrally and passes the final config dict into `initialize(config=...)`.

Resolution order is:

1. project overrides from `MachineConfig.plugin_configs`
2. user config file
3. plugin persisted state
4. environment variable declared in `config_schema`
5. manifest default

This keeps configuration consistent across plugins and avoids each plugin inventing its own loading rules.

## Transport Options

Plugins can run in different ways:

- `in-process`: imported and instantiated directly in Python
- `json-rpc` with `spawn`: started as a subprocess and connected over stdio
- `json-rpc` with `connect`: attached to an already-running process over TCP or Unix socket

That is what makes the overall design language-agnostic. The registry contract is stable even if implementations move out of process.

## Composition Pattern

The intended pattern is:

1. load category-defining framework plugins first
2. load implementation plugins that register concrete behavior
3. compose higher-level plugins on top of those lower-level registrations

For example, a RAG-enabled domain agent might be assembled like this:

- `tool_support` defines `tool`
- `model_provider_support` defines `model_provider`
- `embeddings` defines `embedding`
- `vectorstore_support` defines `vector_store`
- `provider_ollama` registers model provider `ollama`
- `embeddings_ollama` registers embedding provider `ollama`
- `tool_openapi` registers `__openapi_generator__`
- `tool_filter_rag` registers `__filter_rag__`
- `rag_support` registers chunkers, rerankers, and RAG categories
- `agent_runtime_basic` registers agent runtime `basic`
- a domain plugin registers a pipeline and agent that resolve those pieces from the registry

That final domain plugin does not need to own every subsystem itself. It can compose them from the graph.

## Internal Utility Registrations

Some plugins register internal helper implementations into normal categories. Examples include names like `__openapi_generator__` and `__filter_rag__` in the `tool` category.

These are still regular registry entries. The convention is simply that double-underscore names are infrastructure utilities intended for other plugins more than for end users.

## Dependency Philosophy

Dependencies in manifests describe the expected composition, but plugins should still fail gracefully when optional pieces are missing.

Common patterns in this repository:

- lazy resolution at first use instead of startup-time hard failure
- conditional registration when optional third-party packages are unavailable
- domain plugins that degrade cleanly when helper plugins are missing

This keeps projects flexible while still making the preferred composition explicit.

## Authoring Guidance

Good plugins in this repo tend to follow a few rules:

- keep plugin setup small and explicit
- register into existing categories when possible instead of inventing new ones
- define a new category only when the abstraction is genuinely reusable
- use manifests and config schema as the primary contract
- keep domain orchestration in plugins, not in `machine-core`
- prefer composition through `resolve()` over direct imports between plugins

## Relationship To Projects

A typical project only needs:

- a `pyproject.toml` with a `[tool.machine-core]` section
- a short plugin list
- optional per-plugin config overrides
- a tiny bootstrap such as `machine = Machine(config=MachineConfig.from_pyproject())`

That project becomes powerful because the selected plugins collectively define its runtime behavior.

## Goal

The goal of `machine-plugins` is not to be a monolithic framework package. The goal is to provide a growing library of composable building blocks that let projects assemble agents, providers, tools, servers, workflows, RAG pipelines, and support systems from small, explicit plugins.
