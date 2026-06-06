"""Encryption-at-rest for owner-revealable POS PINs.

POS PINs must be readable by the authorized merchant owner (the eye-reveal in Settings) AND survive
a PIN-login, so they cannot be one-way hashed. Storing them in plaintext would expose every PIN in a
DB dump. We therefore encrypt them with **Fernet** (AES-128-CBC + HMAC) under a key held in the
environment — NOT in the database — so a stolen dump is useless without the key.

The key is derived (SHA-256 → urlsafe-base64) from `PIN_SECRET`, falling back to `JWT_SECRET` so
dev/docker work with no extra config. Production should set a distinct `PIN_SECRET` (ideally sourced
from a secrets manager / KMS). Rotating the key re-locks existing PINs — re-issue them after a rotation.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_LEGACY_PLAINTEXT_LEN = range(4, 7)  # 4–6 digits — bridge for rows written before encryption


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    secret = (settings.PIN_SECRET or settings.JWT_SECRET).encode("utf-8")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret).digest()))


def encrypt_pin(plain: str) -> str:
    """Encrypt a plaintext PIN for storage. Same PIN → different ciphertext each call (random IV)."""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def reveal_pin(stored: str | None) -> str | None:
    """Decrypt a stored PIN back to plaintext for the authorized owner / PIN-login. Tolerates legacy
    bare-digit plaintext (rows written before encryption) so they keep working until next rewritten."""
    if not stored:
        return None
    try:
        return _fernet().decrypt(stored.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return stored if stored.isdigit() and len(stored) in _LEGACY_PLAINTEXT_LEN else None
