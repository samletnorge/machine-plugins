from studio_support.context_models import (
    RuntimeAttachment,
    StudioContext,
    StudioEnvironment,
    StudioProject,
    StudioTenant,
)


def test_context_models_capture_hierarchy_and_attachment_state():
    tenant = StudioTenant(id="tenant-northwind", slug="northwind", name="Northwind")
    project = StudioProject(
        id="project-fuel-ops",
        tenant_id="tenant-northwind",
        slug="fuel-ops",
        name="Fuel Ops",
        entry="fuel.main:machine",
        capability_summary={"agents": 18, "tools": 46},
    )
    environment = StudioEnvironment(
        id="env-prod",
        project_id="project-fuel-ops",
        name="prod",
        connection_kind="local",
        connection_ref="fuel-ops-prod",
        status="healthy",
    )
    context = StudioContext(
        tenant_id=tenant.id,
        project_id=project.id,
        environment_id=environment.id,
    )
    attachment = RuntimeAttachment(
        context=context,
        status="attached",
        machine_name="FuelOpsMachine",
        attached_at="2026-05-28T16:00:00Z",
        error=None,
    )

    assert tenant.slug == "northwind"
    assert project.capability_summary["tools"] == 46
    assert environment.connection_ref == "fuel-ops-prod"
    assert attachment.context.environment_id == "env-prod"
    assert attachment.status == "attached"
