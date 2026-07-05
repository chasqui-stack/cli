"""Preflight: report the toolchain, warn — never block.

Provisioning degrades per step anyway (ADR-005), so a missing tool just
means that step prints its manual command later.
"""

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class Check:
    name: str
    found: bool
    detail: str
    hint: str = ""


def _version(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return ""


def run_checks() -> list[Check]:
    checks: list[Check] = []

    for tool, args, hint in [
        ("uv", ["uv", "--version"], "https://docs.astral.sh/uv/ — required for core/gateway"),
        ("node", ["node", "--version"], "Node >=20 — required for the admin panel and the web gateway"),
        ("npm", ["npm", "--version"], "ships with Node"),
        ("git", ["git", "--version"], "needed for the project's first commit"),
        ("psql", ["psql", "--version"], "optional — used to create the database"),
        ("ffmpeg", ["ffmpeg", "-version"], "optional — voice-note transcoding in the gateway"),
    ]:
        found = shutil.which(tool) is not None
        checks.append(
            Check(tool, found, _version(args) if found else "not found", hint)
        )
    return checks
