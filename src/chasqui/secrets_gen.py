"""Secrets the wizard never asks for — generated once per project."""

import secrets
from dataclasses import dataclass, field


def _hex32() -> str:
    return secrets.token_hex(32)


def _urlsafe24() -> str:
    return secrets.token_urlsafe(24)


def _password12() -> str:
    return secrets.token_urlsafe(12)


@dataclass
class GeneratedSecrets:
    jwt_secret_key: str = field(default_factory=_hex32)
    # Shared gateway <-> core secret: ONE value written into BOTH .envs.
    internal_api_key: str = field(default_factory=_urlsafe24)
    # User pastes this into the Meta webhook config — printed in the epilogue.
    wa_verify_token: str = field(default_factory=_urlsafe24)
    # Fallback when the wizard's admin password is left blank.
    admin_password: str = field(default_factory=_password12)
