"""Provisioning: best-effort, resumable, never aborts the scaffold (ADR-005).

Hard ordering invariant: the `.env`s are written BEFORE this runs — the
first `alembic upgrade head` bakes EMBEDDING_DIM into the schema (ADR-001).
Step dependencies: migrate needs the database; the admin seed needs the
migrated schema. A failed step prints its manual command and disables its
dependents; everything independent still runs.
"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import Answers


@dataclass
class StepResult:
    title: str
    ok: bool
    skipped: bool = False
    manual_cmd: str = ""
    detail: str = ""


@dataclass
class Step:
    title: str
    cwd: str  # relative to the project dir
    argv: list[str]
    needs: list[str] = field(default_factory=list)  # titles of prerequisite steps
    env: dict[str, str] = field(default_factory=dict)
    ok_in_stderr: list[str] = field(default_factory=list)  # failure exemptions

    @property
    def manual_cmd(self) -> str:
        return f"cd {self.cwd} && {' '.join(self.argv)}"


def plan(a: Answers, s: GeneratedSecrets) -> list[Step]:
    steps = [
        Step("Install core dependencies (uv sync)", "core", ["uv", "sync"]),
        Step("Install gateway dependencies (uv sync)", "whatsapp", ["uv", "sync"]),
        Step("Install admin dependencies (npm install)", "admin", ["npm", "install"]),
    ]
    if a.pg_is_local:
        steps.append(
            Step(
                "Create database",
                "core",
                [
                    "createdb",
                    "-h", a.pg_host,
                    "-p", str(a.pg_port),
                    "-U", a.pg_user,
                    a.db_name,
                ],
                env={"PGPASSWORD": a.pg_password} if a.pg_password else {},
                ok_in_stderr=["already exists"],
            )
        )
    steps.append(
        Step(
            "Run migrations (alembic upgrade head)",
            "core",
            ["uv", "run", "alembic", "upgrade", "head"],
            needs=["Install core dependencies (uv sync)"],
        )
    )
    steps.append(
        Step(
            "Seed the first admin",
            "core",
            [
                "uv", "run", "python", "scripts/create_admin.py",
                "--email", a.admin_email,
                "--name", a.admin_name,
                "--password", a.admin_password or s.admin_password,
            ],
            needs=["Run migrations (alembic upgrade head)"],
        )
    )
    return steps


def run(project_dir: Path, steps: list[Step], echo=print) -> list[StepResult]:
    results: list[StepResult] = []
    failed: set[str] = set()

    for step in steps:
        blocked = [n for n in step.needs if n in failed]
        if blocked:
            failed.add(step.title)
            results.append(
                StepResult(
                    step.title, ok=False, skipped=True,
                    manual_cmd=step.manual_cmd,
                    detail=f"skipped — needs: {blocked[0]}",
                )
            )
            echo(f"  ⏭  {step.title} (skipped — prerequisite failed)")
            continue

        echo(f"  ⏳ {step.title} …")
        try:
            proc = subprocess.run(
                step.argv,
                cwd=project_dir / step.cwd,
                env={**os.environ, **step.env},
                capture_output=True,
                text=True,
                timeout=900,
            )
            ok = proc.returncode == 0 or any(
                marker in (proc.stderr or "") for marker in step.ok_in_stderr
            )
            detail = "" if ok else (proc.stderr or proc.stdout).strip()[-400:]
        except FileNotFoundError:
            ok, detail = False, f"`{step.argv[0]}` not found on PATH"
        except subprocess.TimeoutExpired:
            ok, detail = False, "timed out"

        if ok:
            echo(f"  ✅ {step.title}")
        else:
            failed.add(step.title)
            echo(f"  ❌ {step.title} — run it yourself later:\n       {step.manual_cmd}")
        results.append(
            StepResult(step.title, ok=ok, manual_cmd=step.manual_cmd, detail=detail)
        )
    return results
