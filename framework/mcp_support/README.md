# mcp_support

Connects machine-core to one or more [Model Context Protocol](https://modelcontextprotocol.io)
servers and registers each server's tools into the `tool` category, so agents
can call them like any other tool.

## Config

```toml
[tool.machine-core.plugin_configs.mcp_support]
servers = [
  { name = "filesystem", command = "npx", args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"] },
  { name = "git", command = "uvx", args = ["mcp-server-git", "--repository", "."] },
]
```

The same value can be provided as JSON in the `MCP_SERVERS` environment variable.

Tools are registered as `<server>__<tool>` (for example `filesystem__read_file`).
Requires the `mcp` Python SDK (`pip install "mcp>=1.0"`).
