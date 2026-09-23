# MCP

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) lets an agent call tools
hosted by an external server. `mcp_support` connects to one or more MCP servers, lists their
tools, and registers each one into the `tool` category — so agents use them like any other
tool.

## Enable it

```toml
plugins = ["mcp_support", "tool_support", "agent_support", "..."]
```

`mcp_support` declares the dependency `mcp>=1.0`. `uv sync` installs it for you; to install
manually, `pip install "mcp>=1.0"`.

## Configure servers

Declare servers under `[tool.machine-core.plugin_configs.mcp_support]`:

```toml
[tool.machine-core.plugin_configs.mcp_support]
servers = [
  { name = "filesystem", command = "npx", args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"] },
  { name = "git", command = "uvx", args = ["mcp-server-git", "--repository", "."] },
]
```

Each entry supports `name`, `command`, `args`, `env`, and `cwd`. If `name` is omitted, the
`command` is used as the server name.

The same value can be provided as a JSON array in the `MCP_SERVERS` environment variable,
which is handy for containers:

```bash
export MCP_SERVERS='[{"name":"git","command":"uvx","args":["mcp-server-git","--repository","."]}]'
```

## How tools are named

Each MCP tool is registered as `<server>__<tool>`. For example, a `read_file` tool on the
`filesystem` server becomes:

```
tool/filesystem__read_file
```

The registered `ToolDefinition` carries metadata:

```python
{
    "source": "mcp",
    "server": server_name,
    "tool": tool.name,
}
```

Its handler calls `tools/call` on the server and joins the text content blocks into a
string.

## Using MCP tools with an agent

Reference the tool names in `AgentDefinition.tool_refs`:

```python
AgentDefinition(
    name="coder",
    description="A coding assistant with filesystem and git access.",
    model_ref="deepseek/deepseek-chat",
    tool_refs=["filesystem__read_file", "git__git_status"],
    instruction="Use the tools to inspect the repository before answering.",
)
```

Because MCP tools are registered as `ToolDefinition`s with handlers, the basic agent runtime
can call them directly.

> **Note:** Like any `ToolDefinition`, an MCP tool has a `handler`, not an `execute` method,
> so it is not executable through `POST /api/tool/{name}/execute`. It works with agent
> runtimes and (handler-aware) Studio's tool tester. See [Tools](tools.md#run-a-tool-directly).

## Lifecycle

`mcp_support` opens each server's stdio session in `setup()` and keeps them alive for the
lifetime of the machine. On `shutdown()` it closes the exit stack, which terminates the
sessions.

One server failing to connect logs a warning and does **not** stop the others:

```
mcp_support: failed to connect 'git': ...
```

## Listing what loaded

```bash
curl -s http://127.0.0.1:8008/api/tool | python -m json.tool
```

Look for items whose metadata has `"source": "mcp"`.

## Tips

- Name servers clearly; the prefix becomes part of every tool name the model sees.
- Keep `args` explicit (for example, a repository path) so the server is scoped.
- MCP servers are subprocesses; in containers, make sure the binary (`npx`, `uvx`, ...) is
  installed in the image.

---

**Read next:** [Tools](tools.md) · [Agents](agents.md) · [Workspaces](workspaces.md)

**Source:** `framework/mcp_support/`.
