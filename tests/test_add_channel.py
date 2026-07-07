"""`chasqui add channel` — retrofit a gateway into an existing project (cli#5)."""

from pathlib import Path

from typer.testing import CliRunner

from chasqui import add_channel
from chasqui.cli import app

runner = CliRunner()


def _scaffold(tmp_path, mini_stack, channels="whatsapp"):
    """A generated project to retrofit against (whatsapp-only by default)."""
    result = runner.invoke(
        app,
        [
            "new", "demo", "--defaults", "--skip-provision",
            "--source", str(mini_stack), "--channels", channels,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    return tmp_path / "demo"


def _add(channel, mini_stack, extra=()):
    return runner.invoke(
        app,
        ["add", "channel", channel, "--defaults", "--skip-provision",
         "--source", str(mini_stack), *extra],
        catch_exceptions=False,
    )


def test_add_telegram_to_whatsapp_project(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _scaffold(tmp_path, mini_stack)
    monkeypatch.chdir(project)

    result = _add("telegram", mini_stack)
    assert result.exit_code == 0, result.output

    # the gateway dir landed, with its .env
    tg_env = (project / "telegram" / ".env").read_text()
    core_env = (project / "core" / ".env").read_text()

    # the shared secret is READ from core/.env — byte-identical, not regenerated
    key_line = next(
        line for line in core_env.splitlines() if line.startswith("INTERNAL_API_KEY=")
    )
    assert key_line in tg_env

    # the core got wired, exactly once
    assert core_env.count("CHANNEL_TELEGRAM_SEND_URL=") == 1
    assert "CHANNEL_TELEGRAM_SEND_URL=http://localhost:8001/send" in core_env
    # the existing channel's wiring is untouched
    assert "CHANNEL_WHATSAPP_SEND_URL=" in core_env

    # the epilogue says how to run it and to restart the core
    assert "cd telegram && make dev" in result.output
    assert "Restart the core" in result.output


def test_add_web_uses_npm_and_origins_follow_port(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _scaffold(tmp_path, mini_stack)
    monkeypatch.chdir(project)

    result = _add("web", mini_stack)
    assert result.exit_code == 0, result.output

    web_env = (project / "web" / ".env").read_text()
    assert "WEB_ALLOWED_ORIGINS=http://localhost:8002" in web_env
    assert "PORT=8002" in web_env
    core_env = (project / "core" / ".env").read_text()
    assert "CHANNEL_WEB_SEND_URL=http://localhost:8002/send" in core_env
    # web provisions with npm (skipped here, so it shows as a manual step)
    assert "npm install" in result.output


def test_add_refuses_when_dir_exists(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _scaffold(tmp_path, mini_stack)
    monkeypatch.chdir(project)

    result = _add("whatsapp", mini_stack)  # scaffolded with whatsapp already
    assert result.exit_code == 1
    assert "already exists" in result.output or "already exists" in (result.output or "")


def test_add_refuses_outside_a_project(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)  # empty dir — no core/.env
    result = _add("telegram", mini_stack)
    assert result.exit_code == 1
    assert "core/.env" in result.output


def test_add_rejects_unknown_channel(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _scaffold(tmp_path, mini_stack)
    monkeypatch.chdir(project)
    result = _add("smoke-signals", mini_stack)
    assert result.exit_code == 1
    assert "unknown channel" in result.output
    assert "whatsapp, telegram, web" in result.output


def test_add_requires_internal_api_key(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _scaffold(tmp_path, mini_stack)
    core_env = project / "core" / ".env"
    core_env.write_text(
        "\n".join(
            line for line in core_env.read_text().splitlines()
            if not line.startswith("INTERNAL_API_KEY=")
        )
    )
    monkeypatch.chdir(project)
    result = _add("telegram", mini_stack)
    assert result.exit_code == 1
    assert "INTERNAL_API_KEY" in result.output
    # nothing was half-written
    assert not (project / "telegram").exists()


def test_detect_stack_ref_reads_the_readme(tmp_path):
    (tmp_path / "README.md").write_text(
        "…(generated with `chasqui new`, stack v0.3.0).\n"
    )
    assert add_channel.detect_stack_ref(tmp_path) == "v0.3.0"
    (tmp_path / "README.md").write_text("no tag here\n")
    assert add_channel.detect_stack_ref(tmp_path) is None


def test_read_env_value_skips_comments():
    import textwrap
    env = Path(__import__("tempfile").mkdtemp()) / ".env"
    env.write_text(textwrap.dedent("""\
        # INTERNAL_API_KEY=commented-out
        PORT=8091
        INTERNAL_API_KEY=real-value
    """))
    assert add_channel.read_env_value(env, "INTERNAL_API_KEY") == "real-value"
    assert add_channel.read_env_value(env, "PORT") == "8091"
    assert add_channel.read_env_value(env, "MISSING") is None


def test_wire_core_send_url_is_idempotent(tmp_path):
    core_env = tmp_path / ".env"
    core_env.write_text("INTERNAL_API_KEY=k\n")
    assert add_channel.wire_core_send_url(core_env, "telegram", 8001) is True
    assert add_channel.wire_core_send_url(core_env, "telegram", 8001) is False
    assert core_env.read_text().count("CHANNEL_TELEGRAM_SEND_URL=") == 1


def test_add_respects_core_port_for_core_url(tmp_path, mini_stack, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = _scaffold(tmp_path, mini_stack)
    core_env = project / "core" / ".env"
    core_env.write_text(core_env.read_text().replace("PORT=8090", "PORT=9999"))
    monkeypatch.chdir(project)
    result = _add("telegram", mini_stack)
    assert result.exit_code == 0, result.output
    assert "CORE_URL=http://localhost:9999" in (project / "telegram" / ".env").read_text()
