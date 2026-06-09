"""Per-merchant feature settings (e.g. pipeline_enabled). Stored in merchants.settings JSON."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.tenancy import Merchant
from app.services.jackpot import JACKPOT_SPIN_COST
from app.services.rewards import WHEEL_SPIN_COST

# Per-merchant settings surfaced via /org/settings. Spin-cost defaults mirror the
# service constants — a merchant can override them; the games read the override.
#
# Module flags — which of the 3 modules (Intelligence / Table QR / POS) a merchant runs.
# This is the LEGACY/FALLBACK layer: per-node overrides live on `org_nodes` and resolve through
# `boundaries.resolve_modules` (nearest explicit ancestor wins → falls back here). Defaults: all
# three ON (every current merchant uses our built modules — this is the OUR-POS, not external-POS).
DEFAULTS = {
    "pipeline_enabled": True,
    "wheel_spin_cost": WHEEL_SPIN_COST,
    "jackpot_spin_cost": JACKPOT_SPIN_COST,
    "rewards_enabled": True,
    "qr_ordering_enabled": True,
    "pos_enabled": True,
    "wallet_enabled": False,        # stored-value wallet — opt-in (gated by qr_ordering at resolve time)
    "timezone": "Asia/Singapore",   # the tenant's canonical reporting timezone (the "books")
    # Welcome voucher pack granted on signup (issued by vouchers.issue_welcome_pack). Default off.
    "welcome_voucher": {"enabled": False, "count": 1, "value": 0, "per_period": None,
                        "valid_days": None, "name": "Welcome voucher"},
    # POS receipt company header (configured at the console).
    "receipt": {"company_name": "", "uen": "", "address": "", "phone": "", "footer": "Thank you!"},
}


# The non-sensitive subset any staff member may read to render nav (no spin costs).
NAV_FLAG_KEYS = ("pipeline_enabled", "rewards_enabled", "qr_ordering_enabled", "pos_enabled", "wallet_enabled")


def get_settings(db: Session, *, merchant_id: str) -> dict:
    m = db.get(Merchant, merchant_id)
    if not m:
        raise NotFoundError("Merchant not found", code="merchant_not_found")
    merged = dict(DEFAULTS)
    merged.update(m.settings or {})
    return merged


def get_nav_flags(db: Session, *, merchant_id: str) -> dict:
    """Only the nav-relevant booleans — a projection of the full settings, so a downline
    staffer can render navigation without reading owner-only economic config."""
    full = get_settings(db, merchant_id=merchant_id)
    return {k: full[k] for k in NAV_FLAG_KEYS}


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
