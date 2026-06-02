"""Studio dependencies backed by context-aware Studio state."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from studio_support.attachment import AttachmentManager
from studio_support.context_catalog import StudioContextCatalog, load_context_catalog
from studio_support.context_models import (
    RuntimeAttachment,
    StudioContext,
    StudioEnvironment,
    StudioProject,
    StudioTenant,
)
from studio_support.runtime_client import RemoteMachineClient


@dataclass(slots=True)
class StudioState:
    catalog: StudioContextCatalog
    attachment_manager: AttachmentManager


_request_studio_state: ContextVar[StudioState | None] = ContextVar(
    "studio_request_state", default=None
)
_default_studio_state: ContextVar[StudioState | None] = ContextVar(
    "studio_default_state", default=None
)


def _build_local_machine_resolver(machine: Any) -> Callable[[StudioContext], Any]:
    if hasattr(machine, "resolve_for_context"):
        return machine.resolve_for_context
    if callable(machine) and not hasattr(machine, "list_category"):
        return machine
    if isinstance(machine, Mapping):
        return lambda context: machine[context.environment_id]
    return lambda context: machine


def _build_machine_resolver(
    machine: Any, catalog: StudioContextCatalog
) -> Callable[[StudioContext], Any]:
    local_resolver = _build_local_machine_resolver(machine)
    environments_by_id = {
        environment.id: environment for environment in catalog.environments
    }

    def _resolve(context: StudioContext) -> Any:
        environment = environments_by_id.get(context.environment_id)
        if environment is None:
            raise KeyError(
                f"Studio environment '{context.environment_id}' is not defined"
            )

        kind = environment.connection_kind.lower()
        if kind == "local":
            return local_resolver(context)
        if kind in {"http", "https"} or environment.connection_ref.startswith(
            ("http://", "https://")
        ):
            return RemoteMachineClient(environment.connection_ref)
        raise RuntimeError(
            f"Studio environment '{environment.name}' uses unsupported connection_kind '{environment.connection_kind}'"
        )

    return _resolve


def build_studio_state(machine: Any) -> StudioState:
    root_value = os.environ.get("MACHINE_CORE_ROOT")
    if not root_value:
        raise RuntimeError(
            "Studio state initialization requires MACHINE_CORE_ROOT to be set."
        )

    root = Path(root_value)
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        raise RuntimeError(
            f"Studio state initialization requires {pyproject} to exist."
        )

    catalog = load_context_catalog(root)
    initial_attachment = RuntimeAttachment(
        context=catalog.active_context,
        status="detached",
        machine_name=None,
        attached_at=None,
        error=None,
    )
    attachment_manager = AttachmentManager(
        resolver=_build_machine_resolver(machine, catalog),
        initial_attachment=initial_attachment,
    )
    try:
        initial_attachment = attachment_manager.attach(catalog.active_context)
    except Exception as exc:
        raise RuntimeError(
            f"Studio state initialization initial attach failed: {exc}"
        ) from exc
    if initial_attachment.status != "attached":
        raise RuntimeError(
            "Studio state initialization initial attach failed: "
            f"{initial_attachment.error or 'unknown error'}"
        )
    return StudioState(catalog=catalog, attachment_manager=attachment_manager)


def set_studio_state(state: StudioState) -> None:
    _default_studio_state.set(state)


def reset_studio_state() -> None:
    _default_studio_state.set(None)
    _request_studio_state.set(None)


def bind_studio_state(state: StudioState):
    return _request_studio_state.set(state)


def reset_bound_studio_state(token) -> None:
    _request_studio_state.reset(token)


def get_studio_state() -> StudioState:
    state = _request_studio_state.get() or _default_studio_state.get()
    if state is None:
        raise RuntimeError(
            "Studio state not initialized. Call set_studio_state() first."
        )
    return state


def set_machine(machine: Any) -> None:
    set_studio_state(build_studio_state(machine))


def get_machine() -> Any:
    return get_studio_state().attachment_manager.get_machine()


def get_active_context():
    return get_studio_state().catalog.active_context


def get_runtime_attachment() -> RuntimeAttachment:
    return get_studio_state().attachment_manager.attachment()


def _get_tenant_by_slug(
    catalog: StudioContextCatalog, tenant_slug: str
) -> StudioTenant:
    for tenant in catalog.tenants:
        if tenant.slug == tenant_slug:
            return tenant
    raise HTTPException(status_code=404, detail=f"Tenant '{tenant_slug}' not found")


def _get_project_by_slug(
    catalog: StudioContextCatalog, tenant_id: str, project_slug: str
) -> StudioProject:
    for project in catalog.projects:
        if project.tenant_id == tenant_id and project.slug == project_slug:
            return project
    raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")


def _get_project_by_slug_global(
    catalog: StudioContextCatalog, project_slug: str
) -> StudioProject:
    matches = [project for project in catalog.projects if project.slug == project_slug]
    if not matches:
        raise HTTPException(
            status_code=404, detail=f"Project '{project_slug}' not found"
        )
    if len(matches) > 1:
        raise HTTPException(
            status_code=409,
            detail=f"Project slug '{project_slug}' is ambiguous across tenants",
        )
    return matches[0]


def _get_environment_by_name(
    catalog: StudioContextCatalog, project_id: str, environment_name: str
) -> StudioEnvironment:
    for environment in catalog.environments:
        if (
            environment.project_id == project_id
            and environment.name == environment_name
        ):
            return environment
    raise HTTPException(
        status_code=404, detail=f"Environment '{environment_name}' not found"
    )


def _resolve_context_parts(
    catalog: StudioContextCatalog, context: StudioContext
) -> tuple[StudioTenant, StudioProject, StudioEnvironment]:
    tenant = next(
        (item for item in catalog.tenants if item.id == context.tenant_id),
        None,
    )
    project = next(
        (item for item in catalog.projects if item.id == context.project_id),
        None,
    )
    environment = next(
        (item for item in catalog.environments if item.id == context.environment_id),
        None,
    )
    if tenant is None or project is None or environment is None:
        raise RuntimeError("Studio state contains an unresolved active context.")
    return tenant, project, environment


def normalize_context_payload(state: StudioState) -> dict[str, dict[str, object]]:
    tenant, project, environment = _resolve_context_parts(
        state.catalog, state.catalog.active_context
    )
    attachment = state.attachment_manager.attachment()
    return {
        "context": {
            "tenant_slug": tenant.slug,
            "tenant_name": tenant.name,
            "project_slug": project.slug,
            "project_name": project.name,
            "environment_name": environment.name,
            "environment_status": environment.status,
            "environment_connection_kind": environment.connection_kind,
            "environment_connection_ref": environment.connection_ref,
        },
        "attachment": asdict(attachment),
    }


def list_tenants() -> list[dict[str, object]]:
    return [asdict(tenant) for tenant in get_studio_state().catalog.tenants]


def list_projects(tenant_slug: str) -> list[dict[str, object]]:
    catalog = get_studio_state().catalog
    tenant = _get_tenant_by_slug(catalog, tenant_slug)
    return [
        asdict(project)
        for project in catalog.projects
        if project.tenant_id == tenant.id
    ]


def list_environments(project_slug: str) -> list[dict[str, object]]:
    catalog = get_studio_state().catalog
    project = _get_project_by_slug_global(catalog, project_slug)
    return [
        asdict(environment)
        for environment in catalog.environments
        if environment.project_id == project.id
    ]


def switch_context(
    tenant_slug: str, project_slug: str, environment_name: str
) -> dict[str, dict[str, object]]:
    state = get_studio_state()
    catalog = state.catalog
    tenant = _get_tenant_by_slug(catalog, tenant_slug)
    project = _get_project_by_slug(catalog, tenant.id, project_slug)
    environment = _get_environment_by_name(catalog, project.id, environment_name)
    next_context = StudioContext(
        tenant_id=tenant.id,
        project_id=project.id,
        environment_id=environment.id,
    )
    state.catalog = replace(catalog, active_context=next_context)
    state.attachment_manager.attach(next_context)
    return normalize_context_payload(state)
