"""Flag generation and verification.

Flags are never stored in the repository. They are derived at install time::

    TGOAT{<slug>_<12 hex>}   where   hex = HMAC_SHA256(install_secret, scenario_id)[:12]

The same secret also seeds every scenario's random generator, so one install
always produces the same artefacts, models and flags.
"""

from __future__ import annotations

import hashlib
import hmac
import re

FLAG_PREFIX = "TGOAT"
FLAG_HEX_LENGTH = 12
FLAG_PATTERN = re.compile(r"TGOAT\{[a-z0-9_]+_[0-9a-f]{12}\}")

_SEED_DOMAIN = b"tensorgoat-install-secret:"


def derive_secret_from_seed(seed: str) -> str:
    """Deterministically derive a 32-byte (hex) install secret from ``TENSORGOAT_SEED``."""
    return hashlib.sha256(_SEED_DOMAIN + seed.encode("utf-8")).hexdigest()


def _digest(install_secret: str, message: str) -> bytes:
    key = bytes.fromhex(install_secret)
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def make_flag(install_secret: str, scenario_id: str, slug: str) -> str:
    """Return the flag of ``scenario_id`` for this install."""
    token = _digest(install_secret, scenario_id).hex()[:FLAG_HEX_LENGTH]
    return f"{FLAG_PREFIX}{{{slug}_{token}}}"


def verify_flag(install_secret: str, scenario_id: str, slug: str, candidate: str) -> bool:
    """Constant-time comparison of a submitted flag against the expected one."""
    expected = make_flag(install_secret, scenario_id, slug)
    return hmac.compare_digest(expected.encode("utf-8"), candidate.strip().encode("utf-8"))


def scenario_seed(install_secret: str, scenario_id: str) -> int:
    """Seed for a scenario's random generator (independent from the flag bytes)."""
    return int.from_bytes(_digest(install_secret, "seed:" + scenario_id)[:8], "big")


def find_flags(text: str) -> list[str]:
    """Return every flag-shaped substring found in ``text``."""
    return FLAG_PATTERN.findall(text)
