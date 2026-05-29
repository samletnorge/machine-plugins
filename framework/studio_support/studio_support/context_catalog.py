from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from studio_support.context_models import (
    StudioContext,
    StudioEnvironment,
    StudioProject,
    StudioTenant,
)


@dataclass(slots=True)
class StudioContextCatalog:
    tenants: list[StudioTenant]
    projects: list[StudioProject]
    environments: list[StudioEnvironment]
    active_context: StudioContext


def load_context_catalog(root: Path) -> StudioContextCatalog:
    with (root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)

    studio = data.get("tool", {}).get("machine-core", {}).get("studio", {})
    tenants = [StudioTenant(**item) for item in studio.get("tenants", [])]
    projects = [StudioProject(**item) for item in studio.get("projects", [])]
    environments = [
        StudioEnvironment(**item) for item in studio.get("environments", [])
    ]
    active_context = StudioContext(
        tenant_id=studio["active_tenant"],
        project_id=studio["active_project"],
        environment_id=studio["active_environment"],
    )
    return StudioContextCatalog(
        tenants=tenants,
        projects=projects,
        environments=environments,
        active_context=active_context,
    )
