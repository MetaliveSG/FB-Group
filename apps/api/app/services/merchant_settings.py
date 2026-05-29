"""Per-merchant feature settings (e.g. pipeline_enabled). Stored in merchants.settings JSON."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.tenancy import Merchant
from app.services.jackpot import JACKPOT_SPIN_COST
from app.services.rewards import WHEEL_SPIN_COST

# Per-merchant settings surfaced via /org/settings. Spin-cost defaults mirror the
# service constants — a merchant can override them; the games read the override.
DEFAULTS = {
    "pipeline_enabled": True,
    "wheel_spin_cost": WHEEL_SPIN_COST,
    "jackpot_spin_cost": JACKPOT_SPIN_COST,
}


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
