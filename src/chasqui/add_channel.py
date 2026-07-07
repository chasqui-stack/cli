"""`chasqui add channel <name>` — retrofit a channel gateway into an existing
project (cli#5).

Generated projects are degit snapshots with no upstream, so users who skipped
a channel in the wizard (or scaffolded before it existed) need a retrofit
path. This module composes the same pieces `chasqui new` uses — fetch,
envfiles, provision — against an already-scaffolded tree. The one invariant
that matters: the gateway's INTERNAL_API_KEY is READ from core/.env, never
regenerated (a mismatched key 401s silently at runtime).
"""

import re
import shutil
from pathlib import Path

from chasqui import envfiles, epilogue, fetch, provision
from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import Answers

# `chasqui new` records the scaffold tag in the project README:
# "…(generated with `chasqui new`, stack vX.Y.Z)."
_README_TAG_RE = re.compile(r"stack (v\d+\.\d+\.\d+)")

_ENV_RENDERERS = {
    "whatsapp": envfiles.render_whatsapp_env,
    "telegram": envfiles.render_telegram_env,
    "web": envfiles.render_web_env,
}


class AddChannelError(RuntimeError):
    pass


def read_env_value(path: Path, key: str) -> str | None:
    """First value of `KEY=…` in a dotenv file (comments skipped), or None."""
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        if k.strip() == key:
            return v.strip()
    return None


def detect_project(cwd: Path) -> Path:
    """The project root is wherever core/.env lives (written by chasqui new)."""
    if (cwd / "core" / ".env").is_file():
        return cwd
    raise AddChannelError(
        "this doesn't look like a Chasqui project root (no core/.env found) — "
        "run this from the directory `chasqui new` created"
    )


def detect_stack_ref(project_dir: Path) -> str | None:
    """The stack tag the project was scaffolded from, per its README."""
    readme = project_dir / "README.md"
    if not readme.is_file():
        return None
    match = _README_TAG_RE.search(readme.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def base_answers(project_dir: Path, channel: str) -> Answers:
    """Answers seeded from the existing project: its name and core port."""
    a = Answers(project_name=project_dir.name)
    a.channels = [channel]
    core_port = read_env_value(project_dir / "core" / ".env", "PORT")
    if core_port and core_port.isdigit():
        a.core_port = int(core_port)
    return a


def wire_core_send_url(core_env: Path, channel: str, port: int) -> bool:
    """Append CHANNEL_<CH>_SEND_URL to core/.env; False if already wired."""
    key = f"CHANNEL_{channel.upper()}_SEND_URL"
    if read_env_value(core_env, key) is not None:
        return False
    text = core_env.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    text += (
        f"\n# Added by `chasqui add channel {channel}` (ADR-004)\n"
        f"{key}=http://localhost:{port}/send\n"
    )
    core_env.write_text(text, encoding="utf-8")
    return True


def _gateway_port(a: Answers, channel: str) -> int:
    return {
        "whatsapp": a.gateway_port,
        "telegram": a.telegram_port,
        "web": a.web_port,
    }[channel]


def _provision_step(channel: str) -> provision.Step:
    if channel == "web":
        # The web gateway is a Node monolith (ADR-011) — npm, not uv.
        return provision.Step(
            "Install web gateway dependencies (npm install)", "web", ["npm", "install"]
        )
    return provision.Step(
        f"Install {channel} gateway dependencies (uv sync)", channel, ["uv", "sync"]
    )


def run_add(
    channel: str,
    a: Answers,
    *,
    project_dir: Path,
    ref: str,
    source: Path | None = None,
    skip_provision: bool = False,
    echo=print,
) -> None:
    dest = project_dir / channel
    if dest.exists():
        raise AddChannelError(
            f"{dest} already exists — this project already has the {channel} "
            "channel (delete the directory first if you want a fresh copy)"
        )

    core_env = project_dir / "core" / ".env"
    internal_key = read_env_value(core_env, "INTERNAL_API_KEY")
    if not internal_key:
        raise AddChannelError(
            "core/.env has no INTERNAL_API_KEY — the gateway must share the "
            "core's exact key. Set it in core/.env first, then re-run."
        )
    # Only the shared secret is inherited; per-channel secrets (webhook
    # verify tokens) are fresh, exactly as a wizard run would mint them.
    secrets = GeneratedSecrets(internal_api_key=internal_key)

    echo(f"📦 Fetching {channel} ({'local ' + str(source) if source else ref}) …")
    try:
        fetch.fetch_channel(project_dir, channel, ref=ref, source=source)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise

    echo("🖋  Writing .env + wiring the core …")
    (dest / ".env").write_text(_ENV_RENDERERS[channel](a, secrets), encoding="utf-8")
    port = _gateway_port(a, channel)
    if wire_core_send_url(core_env, channel, port):
        echo(f"  ✅ CHANNEL_{channel.upper()}_SEND_URL added to core/.env")
    else:
        echo(f"  ⏭  CHANNEL_{channel.upper()}_SEND_URL already in core/.env — left as is")

    step = _provision_step(channel)
    if skip_provision:
        echo("⏭  Provisioning skipped (--skip-provision)")
        results = [
            provision.StepResult(step.title, ok=False, skipped=True, manual_cmd=step.manual_cmd)
        ]
    else:
        echo("🔧 Provisioning …")
        results = provision.run(project_dir, [step], echo=echo)

    echo(epilogue.build_add(a, secrets, results, channel))
