"""Back-office password policy — operators + merchant/staff/node accounts.

One place so every back-office account-creation schema enforces the same rule. Customer passwords
(`schemas/auth.py`) are deliberately NOT held to this (consumer UX) — they keep the min-length floor.
"""
from __future__ import annotations

import re

_SPECIAL = re.compile(r"[^A-Za-z0-9]")

MIN_LENGTH = 8


def validate_password_strength(pw: str) -> str:
    """Enforce the back-office password policy and return the value (raises ValueError → 422):
    at least 8 characters, with ≥1 uppercase letter, ≥1 number, and ≥1 special character.
    Use as a Pydantic `field_validator` on back-office password fields."""
    if len(pw) < MIN_LENGTH:
        raise ValueError(f"Password must be at least {MIN_LENGTH} characters")
    if not any(c.isupper() for c in pw):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in pw):
        raise ValueError("Password must contain at least one number")
    if not _SPECIAL.search(pw):
        raise ValueError("Password must contain at least one special character")
    return pw
