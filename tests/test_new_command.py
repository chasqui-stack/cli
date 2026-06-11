"""End-to-end `chasqui new --defaults --skip-provision --source <mini-stack>`."""

import subprocess

from typer.testing import CliRunner

from chasqui.cli import app

runner = CliRunner()


def _run_new(tmp_path, mini_stack, name="demo"):
    return runner.invoke(
        app,
        ["new", name, "--defaults", "--skip-provision", "--source", str(mini_stack)],
        env={"PWD": str(tmp_path)},
        catch_exceptions=False,
    )


def test_new_scaffolds_a_project(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _run_new(tmp_path, mini_stack)
    assert result.exit_code == 0, result.output

    project = tmp_path / "demo"
    assert (project / "core" / ".env").is_file()
    assert (project / "whatsapp" / ".env").is_file()
    assert (project / "admin" / ".env").is_file()
    assert (project / "README.md").is_file()
    assert (project / "docker-compose.yml").is_file()

    # dev artifacts from the source checkout never travel
    assert not (project / "core" / ".venv").exists()
    assert "never copy me" not in (project / "core" / ".env").read_text()

    # branding applied
    assert "service: demo-core" in (project / "core" / "config" / "deploy.yml").read_text()

    # the shared secret is identical in both .envs
    core_env = (project / "core" / ".env").read_text()
    wa_env = (project / "whatsapp" / ".env").read_text()
    key = next(
        line for line in core_env.splitlines() if line.startswith("INTERNAL_API_KEY=")
    )
    assert key in wa_env

    # epilogue tells the user what's pending and how to start
    assert "make dev" in result.output
    assert "Verify token" in result.output


def test_new_inits_git_with_clean_history(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _run_new(tmp_path, mini_stack)
    project = tmp_path / "demo"
    assert (project / ".git").is_dir()
    # the commit happens after every scaffold/provision write — the tree
    # must be born clean
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=project, capture_output=True, text=True
    ).stdout.strip()
    assert dirty == ""
    # .envs must be ignored by the per-service .gitignore
    tracked = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "core/.env"],
        cwd=project,
        capture_output=True,
        text=True,
    ).stdout
    assert "!! core/.env" in tracked


def test_new_refuses_existing_dir(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo").mkdir()
    result = runner.invoke(
        app,
        ["new", "demo", "--defaults", "--skip-provision", "--source", str(mini_stack)],
    )
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_rejects_invalid_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "9bad name!", "--defaults", "--skip-provision"])
    assert result.exit_code == 1
    assert "not a valid project name" in result.output


def test_version_shows_pinned_stack():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "chasqui" in result.output and "stack v" in result.output
