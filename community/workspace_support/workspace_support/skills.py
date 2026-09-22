"""Discoverable skill files for agent specialization.

Skills are markdown files with a specific header format. The SkillsManager
discovers them from a directory, parses metadata, and loads full content on demand.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from pydantic import BaseModel
from loguru import logger


class SkillMetadata(BaseModel):
    """Parsed metadata from a skill markdown file."""

    name: str
    description: str = ""
    when_to_use: list[str] = []
    file_path: str = ""


class SkillsManager:
    """Discover, parse, and load skill files from a directory."""

    def __init__(self, skills_dir: str) -> None:
        self._skills_dir = skills_dir
        self._skills: dict[str, SkillMetadata] = {}

    def discover(self) -> list[SkillMetadata]:
        self._skills.clear()

        if not os.path.isdir(self._skills_dir):
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            return []

        results = []
        for filename in sorted(os.listdir(self._skills_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(self._skills_dir, filename)
            meta = self._parse_file(filepath)
            if meta:
                self._skills[meta.name] = meta
                results.append(meta)

        logger.debug(f"Discovered {len(results)} skills in {self._skills_dir}")
        return results

    def _parse_file(self, filepath: str) -> Optional[SkillMetadata]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read skill file {filepath}: {e}")
            return None

        name_match = re.search(r"^#\s+Skill:\s*(.+)$", content, re.MULTILINE)
        if not name_match:
            return None
        name = name_match.group(1).strip()

        desc_match = re.search(
            r"##\s+Description\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL
        )
        description = desc_match.group(1).strip() if desc_match else ""

        when_match = re.search(
            r"##\s+When to Use\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL
        )
        when_to_use = []
        if when_match:
            for line in when_match.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith("- "):
                    when_to_use.append(line[2:].strip())

        return SkillMetadata(
            name=name,
            description=description,
            when_to_use=when_to_use,
            file_path=filepath,
        )

    def load(self, name: str) -> str:
        meta = self._skills.get(name)
        if meta is None:
            raise KeyError(
                f"Skill '{name}' not found. Available: {list(self._skills.keys())}"
            )
        with open(meta.file_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_metadata(self, name: str) -> SkillMetadata:
        meta = self._skills.get(name)
        if meta is None:
            raise KeyError(f"Skill '{name}' not found")
        return meta

    def list_names(self) -> list[str]:
        return sorted(self._skills.keys())
