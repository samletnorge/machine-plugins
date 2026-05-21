"""PromptRegistry: manage and render prompt templates."""

from __future__ import annotations
from .schemas import PromptBlock, PromptTemplate, RenderedPrompt


class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, dict[str, PromptTemplate]] = {}

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
        text = template.template.format(**full_vars)
        return RenderedPrompt(
            text=text,
            template_name=template.name,
            template_version=template.version,
            variables_used=full_vars,
        )

    def compose(self, blocks: list[PromptBlock]) -> str:
        parts = []
        for block in blocks:
            prefix = f"[{block.role}]" if block.role else ""
            parts.append(f"{prefix} {block.content}".strip())
        return "\n\n".join(parts)

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())
