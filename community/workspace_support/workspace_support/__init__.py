"""workspace_support: Sandbox, filesystem, and skills categories for agent workspaces."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

from .sandbox import Sandbox, ExecutionResult, LocalSandbox, DockerSandbox
from .filesystem import FileSystem, FileInfo, LocalFileSystem
from .skills import SkillMetadata, SkillsManager
from .workspace import AgentWorkspace, WorkspaceConfig

__all__ = [
    "WorkspaceSupportPlugin",
    "Sandbox",
    "ExecutionResult",
    "LocalSandbox",
    "DockerSandbox",
    "FileSystem",
    "FileInfo",
    "LocalFileSystem",
    "SkillMetadata",
    "SkillsManager",
    "AgentWorkspace",
    "WorkspaceConfig",
]


class WorkspaceSupportPlugin:
    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx: PluginContext):
        ctx.register_category(
            "sandbox",
            operations={
                "execute": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )
        ctx.register_category(
            "filesystem",
            operations={
                "read": {"method": "POST", "on": "item"},
                "write": {"method": "POST", "on": "item"},
                "list": {"method": "GET", "on": "collection"},
            },
        )

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
