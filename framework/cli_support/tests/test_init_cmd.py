from __future__ import annotations

import tomllib

from cli_support.commands.init_cmd import init_command


def test_init_command_scaffolds_default_studio_context_catalog(tmp_path):
    project_root = tmp_path / "demo-project"

    init_command(str(project_root))

    with (project_root / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    studio = pyproject["tool"]["machine-core"]["studio"]

    assert studio["active_tenant"] == "tenant-local"
    assert studio["active_project"] == "project-demo-project"
    assert studio["active_environment"] == "env-dev"
    assert studio["tenants"][0]["slug"] == "local"
    assert studio["projects"][0]["slug"] == "demo-project"
    assert studio["environments"][0]["name"] == "dev"
