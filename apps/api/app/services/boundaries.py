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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.org import PATH_SEP, OrgNode
from app.models.orders import Order
from app.services import merchant_settings

# The module flags recorded in Phase 0c (gated for real in Phase 2).
MODULE_FLAGS = ("rewards_enabled", "qr_ordering_enabled", "pos_enabled")

# Module flag → its 3-state org_node column (NULL = inherit).
_MODULE_COL = {
    "rewards_enabled": "mod_rewards",        # Customer Engagement
    "qr_ordering_enabled": "mod_qr_ordering",  # Table QR
    "pos_enabled": "mod_pos",                # POS
}


def loyalty_domain_id(merchant_id: str) -> str:
    """The loyalty domain (free-coin ring) for a merchant. Today the merchant *is* the domain;
    Phase 1 resolves the nearest `is_loyalty_domain` ancestor in the org tree."""
    return merchant_id


def settlement_account_id(db: Session, *, order: Order) -> str:
    """Who the sale settles to. Today = the order's merchant; Phase 2 resolves the venue's
    `settlement_mode` (operator central account vs the individual stall)."""
    return order.merchant_id


def module_flags(db: Session, *, merchant_id: str) -> dict:
    """The adopted-module flags for a merchant (rewards / qr_ordering / pos) from `Merchant.settings`
    (the legacy / fallback layer). Per-node overrides resolve through `resolve_modules`."""
    settings = merchant_settings.get_settings(db, merchant_id=merchant_id)
    return {flag: bool(settings.get(flag, False)) for flag in MODULE_FLAGS}


def _node_chain(db: Session, node: OrgNode) -> list[OrgNode]:
    """`node` + its ancestors, NEAREST-first (node, parent, …, root). Path-prefix, no recursion."""
    ids = node.path.split(PATH_SEP)                       # root-first lineage of node ids
    found = {n.id: n for n in db.scalars(select(OrgNode).where(OrgNode.id.in_(ids))).all()}
    return [found[i] for i in reversed(ids) if i in found]


def resolve_modules(db: Session, *, node: OrgNode | None, merchant_id: str) -> dict:
    """The 3 module flags resolved for a node via the org-tree cascade: the **nearest explicit
    ancestor wins** (NULL = inherit), falling back to the tenant's `Merchant.settings` → defaults
    when no node in the chain sets it. Behaviour-neutral until a node flag is explicitly toggled.

    `node` is the storefront (or any node) the action happens at; `merchant_id` is the funding tenant
    used for the legacy fallback. Returns the same shape as `module_flags`."""
    legacy = module_flags(db, merchant_id=merchant_id)
    chain = _node_chain(db, node) if node is not None else []
    out = {}
    for flag, col in _MODULE_COL.items():
        explicit = None
        for n in chain:
            v = getattr(n, col, None)
            if v is not None:
                explicit = bool(v)
                break
        out[flag] = legacy[flag] if explicit is None else explicit
    return out


def node_for_outlet(db: Session, outlet_id: str | None) -> OrgNode | None:
    """The storefront OrgNode for an outlet — via the `menu.id == node.id` invariant
    (falls back to a node whose id == outlet_id for the legacy/collapsed seed)."""
    if not outlet_id:
        return None
    from app.services import pos_staff
    return pos_staff.node_for_outlet(db, outlet_id)


def resolve_modules_for_outlet(db: Session, *, outlet_id: str | None, merchant_id: str) -> dict:
    """Convenience: resolve the 3 module flags for the node an outlet maps to (cascade + fallback)."""
    return resolve_modules(db, node=node_for_outlet(db, outlet_id), merchant_id=merchant_id)
