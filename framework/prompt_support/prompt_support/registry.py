"""PromptRegistry: manage and render prompt templates."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from .schemas import PromptBlock, PromptTemplate, RenderedPrompt


class PromptRegistry:
    def __init__(self, hook_caller: Callable[..., Any] | None = None) -> None:
        self._templates: dict[str, dict[str, PromptTemplate]] = {}
        self._hook_caller = hook_caller

    def _fire(self, hook_name: str, **kwargs: Any) -> None:
        """Fire a hook best-effort; render() is synchronous."""
        if self._hook_caller is None:
            return
        try:
            result = self._hook_caller(hook_name, **kwargs)
            if hasattr(result, "__await__"):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(result)
                except RuntimeError:
                    result.close()
        except Exception:  # noqa: BLE001 - hooks must not break rendering
            pass

    def register(self, template: PromptTemplate) -> None:
        versions = self._templates.setdefault(template.name, {})
        versions[template.version] = template

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        versions = self._templates.get(name)
        if not versions:
            raise KeyError(f"Prompt template '{name}' not found")
        if version:
            if version not in versions:
                raise KeyError(
                    f"Prompt template '{name}' version '{version}' not found"
                )
            return versions[version]
        latest_version = sorted(versions.keys())[-1]
        return versions[latest_version]

    def render(
        self, name: str, variables: dict, version: str | None = None
    ) -> RenderedPrompt:
        template = self.get(name, version)
        full_vars = {}
        for var in template.variables:
            if var.name in variables:
                full_vars[var.name] = variables[var.name]
            elif var.default is not None:
                full_vars[var.name] = var.default
            elif var.required:
                raise ValueError(
                    f"Missing required variable '{var.name}' for template '{name}'"
                )
        for k, v in variables.items():
            if k not in full_vars:
                full_vars[k] = v
        self._fire(
            "before_prompt_render", template=template, variables=full_vars
        )
        text = template.template.format(**full_vars)
        rendered = RenderedPrompt(
            text=text,
            template_name=template.name,
            template_version=template.version,
            variables_used=full_vars,
        )
        self._fire("after_prompt_render", rendered=rendered)
        return rendered

    def compose(self, blocks: list[PromptBlock]) -> str:
        parts = []
        for block in blocks:
            prefix = f"[{block.role}]" if block.role else ""
            parts.append(f"{prefix} {block.content}".strip())
        return "\n\n".join(parts)

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())
