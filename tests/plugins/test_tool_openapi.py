"""Tests for tool-openapi plugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tool_support.schemas import ToolDefinition

PETSTORE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Petstore", "version": "1.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "tag": {"type": "string"},
                                },
                                "required": ["name"],
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
    },
}


class TestOpenAPIGenerator:
    def test_generate_tools_from_spec(self):
        from tool_openapi.generator import generate_tools

        tools = generate_tools(PETSTORE_SPEC, base_url="https://petstore.example.com")
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "listPets" in names

    def test_tool_has_parameters_schema(self):
        from tool_openapi.generator import generate_tools

        tools = generate_tools(PETSTORE_SPEC, base_url="https://petstore.example.com")
        list_tool = next(t for t in tools if "list" in t.name.lower())
        assert list_tool.parameters
        assert "properties" in list_tool.parameters

    def test_tool_has_handler(self):
        from tool_openapi.generator import generate_tools

        tools = generate_tools(PETSTORE_SPEC, base_url="https://petstore.example.com")
        for tool in tools:
            assert callable(tool.handler)

    def test_tool_metadata(self):
        from tool_openapi.generator import generate_tools

        tools = generate_tools(PETSTORE_SPEC, base_url="https://petstore.example.com")
        list_tool = next(t for t in tools if "list" in t.name.lower())
        assert list_tool.metadata["source"] == "openapi"
        assert list_tool.metadata["path"] == "/pets"
        assert list_tool.metadata["method"] == "get"

    def test_schema_simplification(self):
        from tool_openapi.generator import simplify_schema

        schema = {
            "type": "object",
            "properties": {"pet": {"$ref": "#/components/schemas/Pet"}},
        }
        components = {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
        simplified = simplify_schema(schema, components)
        assert "$ref" not in str(simplified)
        assert "name" in simplified["properties"]["pet"]["properties"]

    def test_simplify_schema_strips_extra_fields(self):
        from tool_openapi.generator import simplify_schema

        schema = {
            "type": "string",
            "title": "Name",
            "default": "Fido",
            "example": "Rex",
        }
        simplified = simplify_schema(schema, {})
        assert "title" not in simplified
        assert "default" not in simplified
        assert "example" not in simplified
        assert simplified["type"] == "string"

    def test_simplify_schema_max_depth(self):
        from tool_openapi.generator import simplify_schema

        schema = {"$ref": "#/components/schemas/A"}
        components = {"schemas": {"A": {"$ref": "#/components/schemas/A"}}}
        result = simplify_schema(schema, components)
        assert result == {"type": "object"}

    @pytest.mark.asyncio
    async def test_tool_handler_makes_http_call(self):
        from tool_openapi.generator import generate_tools

        tools = generate_tools(PETSTORE_SPEC, base_url="https://petstore.example.com")
        list_tool = next(t for t in tools if "list" in t.name.lower())

        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1, "name": "Fido"}]
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tool_openapi.generator.httpx.AsyncClient"
        ) as MockClient:
            client = AsyncMock()
            client.request.return_value = mock_resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client

            result = await list_tool.handler(limit=10)

        assert result == [{"id": 1, "name": "Fido"}]
        client.request.assert_called_once()

    def test_server_url_fallback(self):
        from tool_openapi.generator import generate_tools

        spec = {**PETSTORE_SPEC, "servers": [{"url": "https://custom.api.com"}]}
        tools = generate_tools(spec)
        # Should use the server URL from spec
        assert len(tools) == 2

    def test_empty_spec(self):
        from tool_openapi.generator import generate_tools

        tools = generate_tools({"openapi": "3.0.0", "paths": {}})
        assert tools == []
