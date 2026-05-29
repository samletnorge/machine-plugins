from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from studio_support.app import create_studio_app
from studio_support.attachment import AttachmentManager
from studio_support.context_models import RuntimeAttachment, StudioContext
from studio_support.dependencies import (
    bind_studio_state,
    build_studio_state,
    get_active_context,
    get_machine,
    get_runtime_attachment,
    get_studio_state,
    reset_bound_studio_state,
    reset_studio_state,
    set_studio_state,
    switch_context,
)


class StubMachine:
    name = "FuelOpsMachine"


def _write_studio_pyproject(root: Path, *, project_id: str, machine_ref: str) -> None:
    pyproject = root / "pyproject.toml"
    pyproject.write_text(
        f"""
[tool.machine-core.studio]
active_tenant = "tenant-northwind"
active_project = "{project_id}"
active_environment = "env-prod"

[[tool.machine-core.studio.tenants]]
id = "tenant-northwind"
slug = "northwind"
name = "Northwind"

[[tool.machine-core.studio.projects]]
id = "{project_id}"
tenant_id = "tenant-northwind"
slug = "fuel-ops"
name = "Fuel Ops"
entry = "fuel.main:machine"

[tool.machine-core.studio.projects.capability_summary]
agents = 2
tools = 2

[[tool.machine-core.studio.environments]]
id = "env-prod"
project_id = "{project_id}"
name = "prod"
connection_kind = "local"
connection_ref = "{machine_ref}"
status = "healthy"

[[tool.machine-core.studio.environments]]
id = "env-staging"
project_id = "{project_id}"
name = "staging"
connection_kind = "local"
connection_ref = "{machine_ref}"
status = "healthy"
""".strip()
    )


def test_attachment_manager_switches_to_requested_context():
    initial = StudioContext(
        tenant_id="tenant-acme",
        project_id="project-backoffice",
        environment_id="env-dev",
    )
    target = StudioContext(
        tenant_id="tenant-northwind",
        project_id="project-fuel-ops",
        environment_id="env-prod",
    )
    manager = AttachmentManager(
        resolver=lambda context: StubMachine(),
        initial_attachment=RuntimeAttachment(
            context=initial,
            status="detached",
            machine_name=None,
            attached_at=None,
            error=None,
        ),
    )

    attachment = manager.attach(target)

    assert attachment.status == "attached"
    assert attachment.context == target
    assert attachment.machine_name == "FuelOpsMachine"
    assert manager.get_machine().name == "FuelOpsMachine"


def test_attachment_manager_marks_failure_without_claiming_success():
    initial = StudioContext(
        tenant_id="tenant-acme",
        project_id="project-backoffice",
        environment_id="env-dev",
    )
    target = StudioContext(
        tenant_id="tenant-northwind",
        project_id="project-fuel-ops",
        environment_id="env-prod",
    )

    def resolver(context: StudioContext):
        if context.environment_id == "env-dev":
            return StubMachine()
        raise RuntimeError("boom")

    manager = AttachmentManager(
        resolver=resolver,
        initial_attachment=RuntimeAttachment(
            context=initial,
            status="detached",
            machine_name=None,
            attached_at=None,
            error=None,
        ),
    )
    manager.attach(initial)

    attachment = manager.attach(target)

    assert attachment.context == target
    assert attachment.status == "failed"
    assert attachment.machine_name is None
    assert attachment.attached_at is None
    assert attachment.error == "boom"
    assert manager.get_machine() is None


def test_get_machine_returns_none_for_detached_state():
    previous_state = None
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        pass

    detached_context = StudioContext(
        tenant_id="tenant-detached",
        project_id="project-detached",
        environment_id="env-detached",
    )
    detached_state = SimpleNamespace(
        catalog=SimpleNamespace(active_context=detached_context),
        attachment_manager=AttachmentManager(
            resolver=lambda context: StubMachine(),
            initial_attachment=RuntimeAttachment(
                context=detached_context,
                status="detached",
                machine_name=None,
                attached_at=None,
                error=None,
            ),
        ),
    )

    try:
        set_studio_state(detached_state)

        assert get_machine() is None
    finally:
        if previous_state is None:
            reset_studio_state()
        else:
            set_studio_state(previous_state)


def test_create_studio_app_initializes_context_and_attachment(
    fake_machine, monkeypatch, tmp_path
):
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        previous_state = None

    _write_studio_pyproject(
        tmp_path,
        project_id="project-fuel-ops",
        machine_ref="fake-machine",
    )
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(tmp_path))

    try:
        app = create_studio_app(fake_machine)
        token = bind_studio_state(app.state.studio_state)

        try:
            assert get_active_context().project_id == "project-fuel-ops"
            assert get_runtime_attachment().status == "attached"
            assert get_machine() is fake_machine
        finally:
            reset_bound_studio_state(token)
    finally:
        if previous_state is None:
            reset_studio_state()
        else:
            set_studio_state(previous_state)


def test_create_studio_app_uses_request_local_state_per_app_instance(
    fake_machine, monkeypatch, tmp_path
):
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        previous_state = None

    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    _write_studio_pyproject(
        root_a,
        project_id="project-alpha",
        machine_ref="machine-alpha",
    )
    _write_studio_pyproject(
        root_b,
        project_id="project-beta",
        machine_ref="machine-beta",
    )
    other_machine = SimpleNamespace(name="OtherMachine")

    try:
        monkeypatch.setenv("MACHINE_CORE_ROOT", str(root_a))
        app_a = create_studio_app(fake_machine)

        @app_a.get("/_state")
        def state_a():
            machine = get_machine()
            return {
                "project_id": get_active_context().project_id,
                "machine_name": machine.name,
            }

        monkeypatch.setenv("MACHINE_CORE_ROOT", str(root_b))
        app_b = create_studio_app(other_machine)

        @app_b.get("/_state")
        def state_b():
            machine = get_machine()
            return {
                "project_id": get_active_context().project_id,
                "machine_name": machine.name,
            }

        with TestClient(app_a) as client_a, TestClient(app_b) as client_b:
            assert client_a.get("/_state").json() == {
                "project_id": "project-alpha",
                "machine_name": fake_machine.name,
            }
            assert client_b.get("/_state").json() == {
                "project_id": "project-beta",
                "machine_name": "OtherMachine",
            }
    finally:
        if previous_state is None:
            reset_studio_state()
        else:
            set_studio_state(previous_state)


def test_build_studio_state_requires_machine_core_root(fake_machine, monkeypatch):
    monkeypatch.delenv("MACHINE_CORE_ROOT", raising=False)

    with pytest.raises(RuntimeError, match="MACHINE_CORE_ROOT"):
        build_studio_state(fake_machine)


def test_build_studio_state_requires_pyproject(fake_machine, monkeypatch, tmp_path):
    missing_root = tmp_path / "missing-root"
    missing_root.mkdir()
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(missing_root))

    with pytest.raises(RuntimeError, match="pyproject.toml"):
        build_studio_state(fake_machine)


def test_build_studio_state_surfaces_initial_attach_failure(
    fake_machine, monkeypatch, tmp_path
):
    _write_studio_pyproject(
        tmp_path,
        project_id="project-fuel-ops",
        machine_ref="fake-machine",
    )
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(tmp_path))

    original_attach = AttachmentManager.attach

    def fail_attach(self, context):
        raise ValueError("resolver exploded")

    monkeypatch.setattr(AttachmentManager, "attach", fail_attach)

    with pytest.raises(RuntimeError, match="initial attach failed"):
        build_studio_state(fake_machine)


def test_switch_context_marks_requested_context_failed_without_exposing_stale_runtime(
    fake_machine, monkeypatch, tmp_path
):
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        previous_state = None

    _write_studio_pyproject(
        tmp_path,
        project_id="project-fuel-ops",
        machine_ref="fake-machine",
    )
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(tmp_path))
    studio_state = build_studio_state(fake_machine)
    original_context = studio_state.catalog.active_context
    original_attachment = studio_state.attachment_manager.attachment()
    original_resolver = studio_state.attachment_manager._resolver

    def fail_resolver(context):
        if context.environment_id == "env-staging":
            raise RuntimeError("attach failed")
        return original_resolver(context)

    studio_state.attachment_manager._resolver = fail_resolver

    try:
        set_studio_state(studio_state)

        payload = switch_context(
            tenant_slug="northwind",
            project_slug="fuel-ops",
            environment_name="staging",
        )

        assert payload["context"]["environment_name"] == "staging"
        assert payload["attachment"]["status"] == "failed"
        assert payload["attachment"]["error"] == "attach failed"
        assert studio_state.catalog.active_context != original_context
        assert studio_state.catalog.active_context.environment_id == "env-staging"
        assert get_runtime_attachment() != original_attachment
        assert get_runtime_attachment().context.environment_id == "env-staging"
        assert get_runtime_attachment().status == "failed"
        assert get_machine() is None
    finally:
        if previous_state is None:
            reset_studio_state()
        else:
            set_studio_state(previous_state)


def test_create_studio_app_does_not_overwrite_default_state(
    fake_machine, monkeypatch, tmp_path
):
    previous_state = None
    try:
        previous_state = get_studio_state()
    except RuntimeError:
        pass

    default_context = StudioContext(
        tenant_id="tenant-default",
        project_id="project-default",
        environment_id="env-default",
    )
    default_state = SimpleNamespace(
        catalog=SimpleNamespace(active_context=default_context),
        attachment_manager=AttachmentManager(
            resolver=lambda context: StubMachine(),
            initial_attachment=RuntimeAttachment(
                context=default_context,
                status="detached",
                machine_name=None,
                attached_at=None,
                error=None,
            ),
        ),
    )

    root = tmp_path / "created-app"
    root.mkdir()
    _write_studio_pyproject(
        root,
        project_id="project-created",
        machine_ref="fake-machine",
    )
    monkeypatch.setenv("MACHINE_CORE_ROOT", str(root))

    try:
        set_studio_state(default_state)

        app = create_studio_app(fake_machine)

        assert (
            app.state.studio_state.catalog.active_context.project_id
            == "project-created"
        )
        assert get_active_context().project_id == "project-default"
    finally:
        if previous_state is None:
            reset_studio_state()
        else:
            set_studio_state(previous_state)
