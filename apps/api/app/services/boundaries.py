"""Phase 0d — boundary indirection.

Two boundaries that the platform must resolve, kept as *concepts* so callers stop hard-coding
`merchant_id` for these purposes. Today both resolve to the merchant (single-tenant, flat tree),
so this is behaviour-neutral — but routing through here means Phase 1/2 can change *how* a
boundary is resolved (walk the org tree, honour a per-venue settlement mode) without touching
any call site.

  * **loyalty domain** — the free-coin ring a posting belongs to. Today = the merchant. Phase 1:
    the nearest `is_loyalty_domain` ancestor in the org tree (a group spanning many merchants).
  * **settlement account** — who collects the money for a sale. Today = the merchant. Phase 2:
    resolved by the venue's `settlement_mode` (operator central till vs per-stall).

See `docs/architecture-org-tree.md` §5.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.orders import Order
from app.services import merchant_settings

# The module flags recorded in Phase 0c (gated for real in Phase 2).
MODULE_FLAGS = ("rewards_enabled", "qr_ordering_enabled", "pos_enabled")


def loyalty_domain_id(merchant_id: str) -> str:
    """The loyalty domain (free-coin ring) for a merchant. Today the merchant *is* the domain;
    Phase 1 resolves the nearest `is_loyalty_domain` ancestor in the org tree."""
    return merchant_id


def settlement_account_id(db: Session, *, order: Order) -> str:
    """Who the sale settles to. Today = the order's merchant; Phase 2 resolves the venue's
    `settlement_mode` (operator central account vs the individual stall)."""
    return order.merchant_id


def module_flags(db: Session, *, merchant_id: str) -> dict:
    """The adopted-module flags for a merchant (rewards / qr_ordering / pos). Phase 2 gates
    behaviour on these; Phase 1 moves them to per-node org_node columns inherited down-tree."""
    settings = merchant_settings.get_settings(db, merchant_id=merchant_id)
    return {flag: bool(settings.get(flag, False)) for flag in MODULE_FLAGS}
