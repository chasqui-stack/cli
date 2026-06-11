"""Shared fixtures — a minimal fake stack checkout for `--source` runs."""

import pytest


@pytest.fixture
def mini_stack(tmp_path):
    """The smallest tree that looks like a chasqui parent checkout."""
    root = tmp_path / "stack"

    core = root / "core"
    (core / "config").mkdir(parents=True)
    (core / "app" / "modules").mkdir(parents=True)
    (core / "scripts").mkdir()
    (core / "config" / "deploy.yml").write_text(
        "service: chasqui-core\n"
        "image: your-username/chasqui-core\n"
        "  - 203.0.113.10\n"
        'host: "api.example.com"\n'
        "POSTGRES_DB: chasqui\n"
        'db-terminal: psql -U postgres -d chasqui\n'
    )
    (core / "config" / "init.sql").write_text(
        "-- PostgreSQL initialization for Chasqui core\n"
        "GRANT ALL PRIVILEGES ON DATABASE chasqui TO postgres;\n"
    )
    (core / ".gitignore").write_text(".env\n.venv/\n")
    (core / ".env.example").write_text("APP_NAME=Chasqui Core\n")

    whatsapp = root / "whatsapp"
    (whatsapp / "config").mkdir(parents=True)
    (whatsapp / "config" / "deploy.yml").write_text(
        "service: chasqui-whatsapp\n"
        "image: your-username/chasqui-whatsapp\n"
        '  CORE_URL: "https://api.example.com"\n'
        'host: "wsp.example.com"\n'
    )
    (whatsapp / ".gitignore").write_text(".env\n")

    admin = root / "admin"
    (admin / "config").mkdir(parents=True)
    (admin / "package.json").write_text('{\n  "name": "chasqui-admin"\n}\n')
    (admin / "config" / "deploy.yml").write_text(
        "service: chasqui-admin\n"
        'host: "admin.example.com"\n'
    )
    (admin / ".gitignore").write_text(".env\n")

    # dev artifacts that must NOT be copied into a generated project
    (core / ".venv").mkdir()
    (core / ".venv" / "marker").write_text("never copy me")
    (core / ".env").write_text("SECRET=never copy me")

    (root / "docker-compose.yml").write_text("services: {}\n")
    return root
