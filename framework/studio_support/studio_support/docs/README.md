# machine-core documentation

Welcome to the machine-core documentation. machine-core is a small, language-agnostic
plugin kernel for building AI agent runtimes. This doc set takes you from "what is this?"
to a deployed, working product, following the same path the real CLI and plugins take.

> **New here?** Read [Introduction](introduction.md), then follow
> [Installation](getting-started/installation.md) and the
> [Quickstart](getting-started/quickstart.md). You can have an agent answering in the
> browser in about ten minutes.

## Start here

| Page | What it covers |
|------|----------------|
| [Introduction](introduction.md) | What machine-core is, the kernel + plugins mental model, and what you can build. |
| [Installation](getting-started/installation.md) | Installing the `machine` CLI, scaffolding a project, and running `machine dev` / `machine studio`. |
| [Quickstart](getting-started/quickstart.md) | Zero to a running agent with a tool and a chat UI in one page. |
| [Project anatomy](getting-started/project-anatomy.md) | The generated project layout, `[tool.machine-core]`, `src/main.py`, and `when_ready`. |

## Concepts

| Page | What it covers |
|------|----------------|
| [Architecture](concepts/architecture.md) | The registry, the plugin lifecycle, transports, and how a `Machine` boots. |
| [Plugins](concepts/plugins.md) | Manifests, capabilities, config, and how plugins collaborate. |
| [Hooks and events](concepts/hooks-and-events.md) | Ask-and-collect hooks vs. fire-and-forget events. |
| [Configuration](concepts/configuration.md) | The five-step config resolution chain and `[tool.machine-core]`. |
| [Secrets](concepts/secrets.md) | `.env` and Infisical bootstrap via `bootstrap_secrets()`. |

## Guides

### Build an agent

- [Agents](guides/agents.md) — the `agent` category, `AgentDefinition`, and runtimes.
- [Tools](guides/tools.md) — the `tool` category and the `@tool` decorator.
- [Model providers](guides/model-providers.md) — Ollama, DeepSeek, Groq, Gemini, and more.
- [Memory](guides/memory.md) — threads, working memory, facts, and windowing.
- [RAG](guides/rag.md) — chunking, embedding, retrieval, reranking, and GraphRAG.
- [Workflows](guides/workflows.md) — steps, DAGs, execution engines, and resumption.
- [MCP](guides/mcp.md) — expose Model Context Protocol servers as tools.
- [Voice](guides/voice.md) — speech in, agent, speech out.
- [Browser](guides/browser.md) — Playwright and Stagehand automation as tools.
- [Workspaces](guides/workspaces.md) — sandboxes, filesystems, and skills.
- [Deployers](guides/deployers.md) — Docker, Dokploy, Vercel, and Cloudflare.

### Operate and ship

- [Studio](guides/studio.md) — the Studio control plane: domains, context switching, chat.
- [HTTP API](guides/http-api.md) — auto-generated `/api/{category}` routes, `/health`, and the
  OpenAI-compatible `/gateway/chat/completions`.
- [Evals](guides/evals.md) — running evaluations against a dataset.

### End-to-end tutorials

- [Build a chatbot](guides/build-a-chatbot.md)
- [Build a RAG assistant](guides/build-a-rag-assistant.md)
- [Build a tool-using agent](guides/build-a-tool-using-agent.md)
- [Write a plugin](guides/write-a-plugin.md)

## Reference

| Page | What it covers |
|------|----------------|
| [CLI](reference/cli.md) | Every `machine` command and option. |
| [Manifest](reference/manifest.md) | Every `manifest.json` field. |
| [Registry](reference/registry.md) | `registry.json`, tiers, and plugin install. |
| [Config schema](reference/config-schema.md) | `config_schema` entry types and coercion. |

## Deployment

- [Self-hosting](deployment/self-hosting.md) — run a project and Studio on your own box.
- [Cloud](deployment/cloud.md) — Docker, Dokploy, Vercel, and Cloudflare deployers.

## Help

- [FAQ](faq.md)
- [Troubleshooting](troubleshooting.md)

---

### About these docs

These pages are grounded in the actual source of the `machine-core` kernel and the
`machine-plugins` catalog. Where behavior is surprising or a known rough edge exists, it is
called out in a blockquote so you are not left guessing. See the end of each page for links
to the exact files involved.

The kernel-level deep dives live alongside this set:

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — kernel registry, lifecycle, capabilities, config,
  hooks vs. events, and transports.
- [`GETTING_STARTED.md`](GETTING_STARTED.md) — the previous single-page getting-started guide.
