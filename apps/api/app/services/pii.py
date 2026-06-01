"""Field-level PII masking for CRM views (PII governance, P1).

Raw customer identifiers — phone, email, birthday — are shown only to callers holding
`crm.pii.view` (the merchant owner + platform operators with full drill-in). Everyone else
with `crm.view` (brand/outlet managers, read-only operators) sees masked values: they can
still operate on a customer (tags, tasks, segments, ownership) without reading raw PII.

PDPA data-minimisation: limit who can read personal data to those who need it. Masking is a
pure presentation transform applied at the serialization boundary — the DB still holds the
real values; nothing here mutates data.
"""
from __future__ import annotations

from datetime import date

_BULLETS = "•••"


def mask_email(email: str | None) -> str | None:
    """`john@gmail.com` -> `j•••@gmail.com` (first char + domain visible)."""
    if not email:
        return email
    local, sep, domain = email.partition("@")
    if not sep or not domain:
        return _BULLETS
    head = local[0] if local else ""
    return f"{head}{_BULLETS}@{domain}"


def mask_phone(phone: str | None) -> str | None:
    """`+6581234567` -> `+65•••4567` (country/prefix + last 4 visible)."""
    if not phone:
        return phone
    if len(phone) <= 7:
        return _BULLETS
    return f"{phone[:3]}{_BULLETS}{phone[-4:]}"


def mask_birthday(_birthday: date | None) -> None:
    """Birthday is fully hidden when masked (no age band in v1)."""
    return None
