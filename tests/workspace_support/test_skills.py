"""Tests for the skills discovery and parsing system."""

import os
import tempfile
import pytest
from workspace_support.skills import (
    SkillMetadata,
    SkillsManager,
)


SAMPLE_SKILL = """\
# Skill: systematic-debugging

## Description
Use when encountering any bug, test failure, or unexpected behavior.

## When to Use
- Bug reports
- Test failures
- Unexpected behavior

## Instructions
1. Reproduce the issue
2. Gather evidence
3. Form hypothesis
4. Test hypothesis
"""

SAMPLE_SKILL_2 = """\
# Skill: test-driven-development

## Description
Use when implementing any feature or bugfix.

## When to Use
- New features
- Bug fixes

## Instructions
1. Write a failing test
2. Implement minimal code
3. Refactor
"""


@pytest.fixture
def skills_dir():
    d = tempfile.mkdtemp(prefix="machine_skills_")
    with open(os.path.join(d, "debugging.md"), "w") as f:
        f.write(SAMPLE_SKILL)
    with open(os.path.join(d, "tdd.md"), "w") as f:
        f.write(SAMPLE_SKILL_2)
    with open(os.path.join(d, "readme.txt"), "w") as f:
        f.write("Not a skill")
    yield d
    import shutil

    shutil.rmtree(d)


def test_skill_metadata():
    m = SkillMetadata(
        name="debugging",
        description="Use when encountering bugs",
        when_to_use=["Bug reports", "Test failures"],
        file_path="/path/to/debugging.md",
    )
    assert m.name == "debugging"
    assert len(m.when_to_use) == 2


def test_skills_manager_discover(skills_dir):
    mgr = SkillsManager(skills_dir)
    skills = mgr.discover()
    assert len(skills) == 2
    names = {s.name for s in skills}
    assert "systematic-debugging" in names
    assert "test-driven-development" in names


def test_skills_manager_discover_empty():
    d = tempfile.mkdtemp(prefix="machine_skills_empty_")
    mgr = SkillsManager(d)
    skills = mgr.discover()
    assert skills == []
    import shutil

    shutil.rmtree(d)


def test_skills_manager_load(skills_dir):
    mgr = SkillsManager(skills_dir)
    mgr.discover()
    content = mgr.load("systematic-debugging")
    assert "Reproduce the issue" in content
    assert "# Skill: systematic-debugging" in content


def test_skills_manager_load_unknown(skills_dir):
    mgr = SkillsManager(skills_dir)
    mgr.discover()
    with pytest.raises(KeyError, match="not found"):
        mgr.load("nonexistent-skill")


def test_skills_manager_get_metadata(skills_dir):
    mgr = SkillsManager(skills_dir)
    mgr.discover()
    meta = mgr.get_metadata("test-driven-development")
    assert meta.name == "test-driven-development"
    assert "New features" in meta.when_to_use


def test_skills_manager_list_names(skills_dir):
    mgr = SkillsManager(skills_dir)
    mgr.discover()
    names = mgr.list_names()
    assert sorted(names) == ["systematic-debugging", "test-driven-development"]
