"""Per-merchant feature settings (e.g. pipeline_enabled). Stored in merchants.settings JSON."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.tenancy import Merchant

DEFAULTS = {"pipeline_enabled": True}


def get_settings(db: Session, *, merchant_id: str) -> dict:
    m = db.get(Merchant, merchant_id)
    if not m:
        raise NotFoundError("Merchant not found", code="merchant_not_found")
    merged = dict(DEFAULTS)
    merged.update(m.settings or {})
    return merged


def update_settings(db: Session, *, merchant_id: str, changes: dict) -> dict:
    m = db.get(Merchant, merchant_id)
    if not m:
        raise NotFoundError("Merchant not found", code="merchant_not_found")
    current = dict(m.settings or {})
    for k, v in changes.items():
        if v is not None:
            current[k] = v
    m.settings = current
    db.flush()
    merged = dict(DEFAULTS)
    merged.update(current)
    return merged
