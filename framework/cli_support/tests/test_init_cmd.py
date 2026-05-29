from __future__ import annotations

import tomllib

from cli_support.commands.init_cmd import init_command


def test_init_command_scaffolds_default_studio_context_catalog(tmp_path):
    project_root = tmp_path / "demo-project"

    init_command(str(project_root))

    with (project_root / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    studio = pyproject["tool"]["machine-core"]["studio"]

    assert studio["active_tenant"] == "tenant-samletnorge"
    assert studio["active_project"] == "project-demo-project"
    assert studio["active_environment"] == "env-dev"
    assert [tenant["slug"] for tenant in studio["tenants"]] == [
        "samletnorge",
        "mythrantic",
    ]
    assert [project["slug"] for project in studio["projects"]] == [
        "demo-project",
        "car-expert",
        "news-finder",
        "ai-playground",
    ]
    assert studio["projects"][0]["tenant_id"] == "tenant-samletnorge"
    assert studio["projects"][0]["name"] == "demo-project"
    assert [environment["project_id"] for environment in studio["environments"]] == [
        "project-demo-project",
        "project-car-expert",
        "project-car-expert",
        "project-news-finder",
        "project-news-finder",
        "project-ai-playground",
    ]
    assert studio["environments"][0]["name"] == "dev"
