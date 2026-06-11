"""Branding pass: rename `chasqui` references to the project slug.

An explicit manifest of (file, [(old, new)]) pairs — never a blind sed over
the tree (ADR-005): "chasqui" appears in code identifiers that must NOT
change, and macOS/Linux `sed -i` diverge anyway.
"""

from pathlib import Path

from chasqui.wizard import Answers


def _deploy_pairs(a: Answers, service: str, subdomain: str) -> list[tuple[str, str]]:
    pairs = [(f"chasqui-{service}", f"{a.slug}-{service}")]
    if a.deploy_registry_user:
        pairs.append(("your-username", a.deploy_registry_user))
    if a.deploy_server_ip:
        pairs.append(("203.0.113.10", a.deploy_server_ip))
    if a.deploy_domain:
        pairs += [
            (f"{subdomain}.example.com", f"{subdomain}.{a.deploy_domain}"),
            ("api.example.com", f"api.{a.deploy_domain}"),  # CORE_URL / VITE_API_BASE_URL refs
        ]
    return pairs


def manifest(a: Answers) -> dict[str, list[tuple[str, str]]]:
    db = a.db_name
    return {
        "core/config/deploy.yml": _deploy_pairs(a, "core", "api")
        + [
            ("POSTGRES_DB: chasqui", f"POSTGRES_DB: {db}"),
            ("-d chasqui", f"-d {db}"),
        ],
        "whatsapp/config/deploy.yml": _deploy_pairs(a, "whatsapp", "wsp"),
        "admin/config/deploy.yml": _deploy_pairs(a, "admin", "admin"),
        "core/config/init.sql": [
            ("DATABASE chasqui", f"DATABASE {db}"),
            ("Chasqui core", f"{a.project_name} core"),
        ],
        "admin/package.json": [
            ('"chasqui-admin"', f'"{a.slug}-admin"'),
        ],
    }


def apply(project_dir: Path, a: Answers) -> list[str]:
    """Apply the manifest; returns the relative paths actually touched."""
    touched: list[str] = []
    for rel, pairs in manifest(a).items():
        path = project_dir / rel
        if not path.is_file():
            continue
        text = original = path.read_text(encoding="utf-8")
        for old, new in pairs:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            touched.append(rel)
    return touched
