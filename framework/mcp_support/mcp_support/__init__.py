"""mcp_support: connect to Model Context Protocol servers and expose their tools.

Each configured MCP server is spawned over stdio, its tools are listed, and each
is registered into the ``tool`` category as a ``ToolDefinition`` whose handler
calls ``tools/call`` on the server. Servers are declared in config:

    [tool.machine-core.plugin_configs.mcp_support]
    servers = [
      { name = "filesystem", command = "npx", args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"] },
    ]

(or via the ``MCP_SERVERS`` environment variable as a JSON array.)
"""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class MCPSupportPlugin:
    """Registers tools from external MCP servers into the tool category."""

    def __init__(self) -> None:
        self._servers: list[dict[str, Any]] = []
        self._exit_stack: AsyncExitStack | None = None

    async def initialize(self, config: dict | None = None, **kwargs: Any) -> None:
        config = config or {}
        servers = config.get("servers")
        if isinstance(servers, str):
            try:
                servers = json.loads(servers)
            except json.JSONDecodeError:
                logger.warning("mcp_support: MCP_SERVERS is not valid JSON")
                servers = []
        self._servers = servers or []

    async def setup(self, ctx: PluginContext) -> None:
        for server in self._servers:
            try:
                await self._connect_server(ctx, server)
            except Exception as exc:  # noqa: BLE001 - one bad server must not stop the rest
                logger.warning(
                    "mcp_support: failed to connect '{}': {}",
                    server.get("name", "?"),
                    exc,
                )

    async def _connect_server(
        self, ctx: PluginContext, server: dict[str, Any]
    ) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        from tool_support.schemas import ToolDefinition

        server_name = server.get("name") or server.get("command", "mcp")
        if self._exit_stack is None:
            self._exit_stack = AsyncExitStack()

        params = StdioServerParameters(
            command=server["command"],
            args=server.get("args", []),
            env=server.get("env"),
            cwd=server.get("cwd"),
        )
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        listed = await session.list_tools()
        for tool in getattr(listed, "tools", []) or []:
            name = f"{server_name}__{tool.name}"
            schema = getattr(tool, "inputSchema", None) or getattr(
                tool, "input_schema", None
            )
            ctx.register(
                "tool",
                name,
                ToolDefinition(
                    name=name,
                    description=tool.description or tool.name,
                    parameters=schema or {"type": "object", "properties": {}},
                    handler=self._make_handler(session, tool.name),
                    metadata={
                        "source": "mcp",
                        "server": server_name,
                        "tool": tool.name,
                    },
                ),
            )

    @staticmethod
    def _make_handler(session: Any, tool_name: str) -> Callable[..., Any]:
        async def handler(**kwargs: Any) -> Any:
            result = await session.call_tool(tool_name, kwargs)
            parts: list[str] = []
            for block in getattr(result, "content", []) or []:
                text = getattr(block, "text", None)
                parts.append(text if text is not None else str(block))
            return "\n".join(parts) if parts else result

        return handler

    async def shutdown(self, **kwargs: Any) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
            self._exit_stack = None
