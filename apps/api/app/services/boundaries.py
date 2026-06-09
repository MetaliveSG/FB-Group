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

# Module flag → its org_node column (binary on/off, parent-gated).
_MODULE_COL = {
    "rewards_enabled": "mod_rewards",        # Intelligence
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
    """The 3 module flags resolved for a node — **binary + parent-gated**: a module is ON for a node
    only if the node AND every ancestor have it ON (`effective = AND of own-flags up the path`).
    Turning a node OFF locks its whole subtree OFF; a child can be ON only under an ON parent.

    `node=None` (a collapsed/legacy storefront with no spine node, or a tenant-level summary with no
    specific node) falls back to the tenant's `Merchant.settings` → defaults — unchanged.

    `node` is the storefront (or any node) the action happens at; `merchant_id` is the funding tenant
    used for the node=None fallback. Returns the same shape as `module_flags`."""
    if node is None:
        return module_flags(db, merchant_id=merchant_id)
    chain = _node_chain(db, node)                          # node + ancestors (nearest-first)
    return {flag: all(bool(getattr(n, col)) for n in chain) for flag, col in _MODULE_COL.items()}


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


# --- per-node toggle get/set (the NodeDetailDrawer "Modules" section) ---------------------------

def _parent_enabled(db: Session, node: OrgNode) -> dict:
    """Each module's effective value at the node's PARENT (the gate): a child can be ON only if the
    parent is ON. A root node (no parent) is ungated → all True."""
    parent = db.get(OrgNode, node.parent_id) if node.parent_id else None
    if parent is None:
        return {flag: True for flag in _MODULE_COL}
    return resolve_modules(db, node=parent, merchant_id=node.settlement_account_id)


def get_node_modules(db: Session, node: OrgNode) -> dict:
    """The node's OWN binary on/off per module + the RESOLVED effective values (after parent-gating)
    + `parent_enabled` (whether each module is ON at the parent — drives the grey/lock in the grid)."""
    return {
        "rewards": bool(node.mod_rewards),
        "qr_ordering": bool(node.mod_qr_ordering),
        "pos": bool(node.mod_pos),
        "resolved": resolve_modules(db, node=node, merchant_id=node.settlement_account_id),
        "parent_enabled": _parent_enabled(db, node),
    }


def set_node_modules(db: Session, node: OrgNode, *, rewards: bool | None = None,
                     qr_ordering: bool | None = None, pos: bool | None = None) -> dict:
    """Set a node's per-module binary on/off. Omitted fields are left unchanged. Turning a node OFF
    cascades OFF to the whole subtree via parent-gating (no extra writes — `resolve_modules` AND-gates)."""
    if rewards is not None:
        node.mod_rewards = bool(rewards)
    if qr_ordering is not None:
        node.mod_qr_ordering = bool(qr_ordering)
    if pos is not None:
        node.mod_pos = bool(pos)
    db.flush()
    return get_node_modules(db, node)
