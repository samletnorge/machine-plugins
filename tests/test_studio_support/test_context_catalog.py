from pathlib import Path

from studio_support.context_catalog import load_context_catalog


def test_load_context_catalog_reads_tenants_projects_and_environments(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.machine-core.studio]
active_tenant = "tenant-northwind"
active_project = "project-fuel-ops"
active_environment = "env-prod"

[[tool.machine-core.studio.tenants]]
id = "tenant-northwind"
slug = "northwind"
name = "Northwind"

[[tool.machine-core.studio.projects]]
id = "project-fuel-ops"
tenant_id = "tenant-northwind"
slug = "fuel-ops"
name = "Fuel Ops"
entry = "fuel.main:machine"

[tool.machine-core.studio.projects.capability_summary]
agents = 18
tools = 46

[[tool.machine-core.studio.environments]]
id = "env-prod"
project_id = "project-fuel-ops"
name = "prod"
connection_kind = "local"
connection_ref = "fuel-ops-prod"
status = "healthy"
""".strip()
    )

    catalog = load_context_catalog(tmp_path)

    assert catalog.active_context.project_id == "project-fuel-ops"
    assert catalog.tenants[0].slug == "northwind"
    assert catalog.projects[0].entry == "fuel.main:machine"
    assert catalog.environments[0].name == "prod"
