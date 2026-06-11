"""`chasqui new` orchestration: fetch → rename → .envs → git init → provision."""

import re
import shutil
import subprocess
from pathlib import Path

from chasqui import envfiles, epilogue, fetch, provision, rename
from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import Answers

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

ROOT_GITIGNORE = ".DS_Store\n"

README_TEMPLATE = """# {name}

A WhatsApp AI agent built on the [Chasqui stack](https://github.com/chasqui-stack/chasqui)
(generated with `chasqui new`, stack {tag}).

| Path | Service | Run |
|------|---------|-----|
| `core/` | FastAPI + LangGraph + Postgres/pgvector — the agent | `make dev` (:8090) |
| `whatsapp/` | WhatsApp channel gateway (PyWa) | `make dev` (:8000) |
| `admin/` | Operator panel (React + Vite) | `npm run dev` (:5191) |

Configuration lives in each service's `.env` (written by the wizard): the
LLM provider/model, storage, and notifications are swappable there at any
time. `docker compose up` brings up Postgres + core + admin for
collaborators (`--profile gateway` adds the WhatsApp gateway).

Docs: [architecture](https://github.com/chasqui-stack/chasqui/blob/main/docs/ARCHITECTURE.md)
· [deploy (Kamal)](https://github.com/chasqui-stack/chasqui/blob/main/docs/DEPLOY.md)
"""


class ScaffoldError(RuntimeError):
    pass


def validate_name(name: str) -> str:
    slug = name.lower().replace("_", "-").replace(" ", "-")
    if not SLUG_RE.match(slug):
        raise ScaffoldError(
            f"'{name}' is not a valid project name — use lowercase letters, "
            "digits and dashes, starting with a letter"
        )
    return slug


def run_new(
    a: Answers,
    *,
    target_parent: Path,
    ref: str,
    source: Path | None = None,
    skip_provision: bool = False,
    echo=print,
) -> Path:
    slug = validate_name(a.project_name)
    project_dir = target_parent / slug
    if project_dir.exists():
        raise ScaffoldError(f"{project_dir} already exists")

    secrets = GeneratedSecrets()

    echo(f"📦 Fetching the stack ({'local ' + str(source) if source else ref}) …")
    try:
        fetch.fetch_stack(project_dir, ref=ref, source=source)
    except Exception:
        shutil.rmtree(project_dir, ignore_errors=True)
        raise

    echo("🖋  Branding + writing .env files …")
    rename.apply(project_dir, a)
    (project_dir / "core" / ".env").write_text(
        envfiles.render_core_env(a, secrets), encoding="utf-8"
    )
    (project_dir / "whatsapp" / ".env").write_text(
        envfiles.render_whatsapp_env(a, secrets), encoding="utf-8"
    )
    (project_dir / "admin" / ".env").write_text(
        envfiles.render_admin_env(a), encoding="utf-8"
    )
    from chasqui.stack import STACK_TAG

    (project_dir / "README.md").write_text(
        README_TEMPLATE.format(name=a.project_name, tag=ref or STACK_TAG),
        encoding="utf-8",
    )
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(ROOT_GITIGNORE, encoding="utf-8")

    # First commit BEFORE provisioning: a clean tree (.envs are gitignored
    # per service — secrets never enter history).
    _git_init(project_dir, echo)

    results: list[provision.StepResult] = []
    if skip_provision:
        echo("⏭  Provisioning skipped (--skip-provision)")
        results = [
            provision.StepResult(s.title, ok=False, skipped=True, manual_cmd=s.manual_cmd)
            for s in provision.plan(a, secrets)
        ]
    else:
        echo("🔧 Provisioning …")
        results = provision.run(project_dir, provision.plan(a, secrets), echo=echo)

    echo(epilogue.build(a, secrets, results))
    return project_dir


def _git_init(project_dir: Path, echo=print) -> None:
    if shutil.which("git") is None:
        echo("⚠️  git not found — skipping the initial commit")
        return
    try:
        subprocess.run(
            ["git", "init", "-q", "-b", "main"], cwd=project_dir, check=True, timeout=30
        )
        subprocess.run(["git", "add", "-A"], cwd=project_dir, check=True, timeout=30)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit (chasqui new)"],
            cwd=project_dir,
            check=False,  # commit fails without user.name/email config — non-fatal
            timeout=30,
        )
    except Exception as exc:  # git trouble must not kill the scaffold
        echo(f"⚠️  git init failed ({exc}) — initialize the repo yourself")
