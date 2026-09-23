"""Studio runtime/SPA workspace tests."""

from __future__ import annotations

from pathlib import Path

STUDIO_SUPPORT = (
    Path(__file__).resolve().parents[2]
    / "framework/studio_support/studio_support"
)


def test_spa_project_exists():
    web = STUDIO_SUPPORT / "web"

    assert (web / "package.json").exists()
    assert (web / "vite.config.ts").exists()
    assert (web / "components.json").exists()
    assert (web / "src/routes/+layout.svelte").exists()


def test_spa_build_is_committed():
    build = STUDIO_SUPPORT / "web" / "build"

    assert (build / "index.html").exists()


def test_legacy_templates_and_islands_removed():
    assert not (STUDIO_SUPPORT / "templates").exists()
    assert not (STUDIO_SUPPORT / "static").exists()
    assert not (STUDIO_SUPPORT / "frontend").exists()
