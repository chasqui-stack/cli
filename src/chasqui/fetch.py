"""Degit-style fetch: GitHub tarballs at a pinned tag, no git history.

`--source <path>` swaps the download for a local copy of a stack checkout —
the dev/test escape hatch (codeload only works once the repos are public).
"""

import io
import shutil
import tarfile
from pathlib import Path

import httpx

from chasqui import stack

# Never copy these from a local checkout (dev artifacts / secrets).
_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    ".env",
    ".claude",
    ".kamal",
    ".DS_Store",
)


class FetchError(RuntimeError):
    pass


def _download_tarball(repo: str, ref: str) -> bytes:
    url = stack.CODELOAD_URL.format(org=stack.ORG, repo=repo, ref=ref)
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=60)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(
            f"Could not download {stack.ORG}/{repo}@{ref}: {exc}"
        ) from exc
    return resp.content


def _extract_into(tar_bytes: bytes, dest: Path, only: list[str] | None = None) -> None:
    """Extract a GitHub tarball into dest, stripping the top-level dir."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = member.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            rel = parts[1]
            if only is not None and rel not in only:
                continue
            if member.isdir():
                (dest / rel).mkdir(parents=True, exist_ok=True)
                continue
            if member.issym():
                # e.g. each repo's CLAUDE.md -> AGENTS.md; only relative,
                # intra-repo links are recreated.
                if "/" not in member.linkname and ".." not in member.linkname:
                    target = dest / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.unlink(missing_ok=True)
                    target.symlink_to(member.linkname)
                continue
            if not member.isfile():
                continue  # skip specials
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            target.write_bytes(extracted.read())
            target.chmod(member.mode)


def _dirs_for(channels: list[str] | None) -> dict[str, str]:
    """Always-present services + the selected channel gateways (dir -> repo)."""
    dirs = dict(stack.SERVICES)
    for ch in channels or ["whatsapp"]:
        if ch in stack.CHANNEL_SERVICES:
            dirs[ch] = stack.CHANNEL_SERVICES[ch]
    return dirs


def fetch_stack(
    dest: Path, ref: str, source: Path | None = None, channels: list[str] | None = None
) -> None:
    """Lay the core + admin + selected channel gateways + parent root files under dest."""
    dirs = _dirs_for(channels)
    if source is not None:
        _copy_local(source, dest, dirs)
        return
    for dirname, repo in dirs.items():
        _extract_into(_download_tarball(repo, ref), dest / dirname)
    _extract_into(
        _download_tarball(stack.PARENT_REPO, ref),
        dest,
        only=stack.PARENT_ROOT_FILES,
    )


def _copy_local(source: Path, dest: Path, dirs: dict[str, str]) -> None:
    source = source.expanduser().resolve()
    for dirname in dirs:
        src_dir = source / dirname
        if not src_dir.is_dir():
            raise FetchError(f"--source {source} has no {dirname}/ directory")
        shutil.copytree(src_dir, dest / dirname, ignore=_COPY_IGNORE)
    for root_file in stack.PARENT_ROOT_FILES:
        src_file = source / root_file
        if src_file.is_file():
            shutil.copy2(src_file, dest / root_file)
