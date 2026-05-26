"""Tests for structured_output builtin plugin."""

import pytest
from pydantic import BaseModel
from structured_output.schemas import (
    GenerateObjectRequest,
    GenerateObjectResponse,
)


class PersonSchema(BaseModel):
    name: str
    age: int


def test_generate_object_request():
    req = GenerateObjectRequest(
        model_ref="openai/gpt-4o",
        output_schema=PersonSchema,
        prompt="Extract the person info from: John is 30 years old.",
    )
    assert req.model_ref == "openai/gpt-4o"
    assert req.output_schema is PersonSchema
    assert req.max_retries == 3


def test_generate_object_request_with_instruction():
    req = GenerateObjectRequest(
        model_ref="anthropic/claude-sonnet-4-20250514",
        output_schema=PersonSchema,
        prompt="John is 30.",
        system_instruction="Extract structured data.",
        max_retries=5,
    )
    assert req.system_instruction == "Extract structured data."
    assert req.max_retries == 5


def test_generate_object_response():
    person = PersonSchema(name="John", age=30)
    resp = GenerateObjectResponse(
        object=person,
        raw_output='{"name": "John", "age": 30}',
        retries=0,
        model_ref="openai/gpt-4o",
        duration_ms=250.0,
    )
    assert resp.object.name == "John"
    assert resp.retries == 0


def test_generate_object_response_with_retries():
    person = PersonSchema(name="Jane", age=25)
    resp = GenerateObjectResponse(
        object=person,
        raw_output='{"name": "Jane", "age": 25}',
        retries=2,
        model_ref="openai/gpt-4o",
    )
    assert resp.retries == 2


async def test_plugin_setup_registers_category():
    from machine_core import Machine
    from machine_core.plugin.manifest import PluginManifest, TransportConfig

    m = Machine()
    manifest = PluginManifest(
        name="structured_output",
        version="0.5.0",
        capabilities=[
            "categories:define",
            "hooks:define",
            "events:emit",
            "structured_output:register",
        ],
        transport=TransportConfig(
            type="in-process",
            entry_point="structured_output:StructuredOutputPlugin",
        ),
    )
    m.plugins.register_manifest(manifest)
    await m.plugins.load("structured_output")
    assert "structured_output" in m._registry
    assert "before_generate_object" in m.hooks._specs
    assert "after_generate_object" in m.hooks._specs
    assert "on_validation_retry" in m.hooks._specs
