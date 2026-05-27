"""Task 11 — machine studio command tests."""

from unittest.mock import patch

from typer.testing import CliRunner

from cli_support.main import app

runner = CliRunner()


def test_studio_help():
    result = runner.invoke(app, ["studio", "--help"])
    assert result.exit_code == 0
    assert "studio" in result.output.lower()


def test_studio_no_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch.dict("sys.modules", {"studio_support": None}):
        result = runner.invoke(app, ["studio"])
    assert result.exit_code == 1
    assert "studio_support" in result.output


def test_studio_prefers_explicit_pythonpath_for_studio_support(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".venv" / "bin").mkdir(parents=True)
    (project / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    (project / "pyproject.toml").write_text(
        "[tool.machine-core]\nentry='src.main:machine'\n"
    )

    worktree_studio = tmp_path / "worktree_studio"
    (worktree_studio / "studio_support").mkdir(parents=True)
    (worktree_studio / "studio_support" / "__init__.py").write_text("__all__ = []\n")

    installed_studio = tmp_path / "installed_studio"
    (installed_studio / "studio_support").mkdir(parents=True)
    (installed_studio / "studio_support" / "__init__.py").write_text("__all__ = []\n")

    monkeypatch.chdir(project)
    monkeypatch.setenv("PYTHONPATH", str(worktree_studio))

    calls = []
    generated = {}

    def fake_run(cmd, cwd=None, env=None):
        calls.append((cmd, cwd, env))
        generated["text"] = (Path(cwd) / "_machine_studio_server.py").read_text()
        return 0

    fake_module = type(
        "FakeStudioModule",
        (),
        {"__file__": str(installed_studio / "studio_support" / "__init__.py")},
    )

    with (
        patch("cli_support.commands.studio_cmd.sync_manifests"),
        patch("cli_support.commands.studio_cmd.subprocess.run", side_effect=fake_run),
        patch.dict("sys.modules", {"studio_support": fake_module}),
    ):
        result = runner.invoke(app, ["studio"])

    assert result.exit_code == 0
    assert calls[0][1] == str(project)
    assert str(worktree_studio) in generated["text"]
    assert str(installed_studio) not in generated["text"]
