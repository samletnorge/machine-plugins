"""Message building and OpenAI-format tool-call parsing for the basic runtime."""

from __future__ import annotations

from typing import Any

from tool_support.schemas import ToolDefinition


def build_system_message(instruction: str) -> dict[str, str]:
    return {"role": "system", "content": instruction}


def build_user_message(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def build_tool_result_message(tool_call_id: str, content: str) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def tools_to_openai_schema(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert ToolDefinitions to OpenAI function-calling format."""
    result = []
    for td in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": td.name,
                    "description": td.description,
                    "parameters": td.parameters or {"type": "object", "properties": {}},
                },
            }
        )
    return result
