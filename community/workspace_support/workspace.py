"""Agent workspace — isolated environment per agent.

Combines a FileSystem, Sandbox, and SkillsManager into a single
workspace that agents use for file I/O, code execution, and
skill-based specialization.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from loguru import logger

from .filesystem import FileSystem, LocalFileSystem
from .sandbox import Sandbox, LocalSandbox
from .skills import SkillsManager


class WorkspaceConfig(BaseModel):
    """Configuration for an AgentWorkspace."""

    root_dir: str
    ephemeral: bool = True
    skills_dir: Optional[str] = None
    sandbox_type: str = "local"


class AgentWorkspace:
    """Isolated workspace for an agent."""

    def __init__(
        self,
        config: WorkspaceConfig,
        filesystem: FileSystem,
        sandbox: Sandbox,
        skills: Optional[SkillsManager] = None,
    ) -> None:
        self.config = config
        self.filesystem = filesystem
        self.sandbox = sandbox
        self.skills = skills

    @classmethod
    def create(cls, config: WorkspaceConfig) -> AgentWorkspace:
        filesystem = LocalFileSystem(root=config.root_dir)
        sandbox = LocalSandbox(work_dir=config.root_dir)

        skills = None
        if config.skills_dir:
            skills = SkillsManager(config.skills_dir)
            skills.discover()

        logger.debug(
            f"AgentWorkspace created at {config.root_dir} (ephemeral={config.ephemeral})"
        )
        return cls(config=config, filesystem=filesystem, sandbox=sandbox, skills=skills)

    async def cleanup(self) -> None:
        await self.sandbox.cleanup()
        logger.debug(f"AgentWorkspace cleaned up: {self.config.root_dir}")

    async def __aenter__(self) -> AgentWorkspace:
        return self

    async def __aexit__(self, *args) -> None:
        await self.cleanup()
