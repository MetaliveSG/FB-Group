"""Build & query the org spine (`org_nodes`) — the member-tree-map.

`sync_org_tree` keeps the spine in sync with the typed tables (Merchant/Brand/Outlet/Menu),
idempotently (upsert keyed by id, like the seed bolt-ons). It is the single place that derives
`path`/`depth`/flags, so the tree invariants live in one function. Read paths use the path-prefix
helpers (`sellable_under`, `subtree`) instead of recursive walks.

Today the tree is the fixed chain merchant → brand → outlet → stall(menu); the *shape* is
generic (adjacency + path), so deeper/ragged trees are an additive change later.
"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.catalog import Menu
from app.models.org import PATH_SEP, OrgNode
from app.models.tenancy import Brand, Merchant, Outlet

ROLE_MERCHANT = "MERCHANT"
ROLE_BRAND = "BRAND"
ROLE_OUTLET = "OUTLET"
ROLE_STALL = "STALL"


def _upsert(db: Session, *, node_id: str, parent_id: str | None, role: str, depth: int,
            path: str, sells: bool, loyalty_domain_id: str, settlement_account_id: str,
            is_settlement_boundary: bool, is_loyalty_domain: bool, is_active: bool) -> OrgNode:
    node = db.get(OrgNode, node_id)
    if node is None:
        node = OrgNode(id=node_id)
        db.add(node)
    node.parent_id = parent_id
    node.role = role
    node.depth = depth
    node.path = path
    node.sells = sells
    node.loyalty_domain_id = loyalty_domain_id
    node.settlement_account_id = settlement_account_id
    node.is_settlement_boundary = is_settlement_boundary
    node.is_loyalty_domain = is_loyalty_domain
    node.is_active = is_active
    return node


def sync_org_tree(db: Session) -> dict:
    """Idempotently mirror the typed tables into the spine. Safe to run repeatedly; returns
    a small counts summary. Boundaries resolve to the merchant today (single-tenant tree)."""
    counts = {"merchant": 0, "brand": 0, "outlet": 0, "stall": 0}

    # Merchants — roots; each is its own loyalty domain + settlement account today.
    for m in db.scalars(select(Merchant)).all():
        _upsert(db, node_id=m.id, parent_id=None, role=ROLE_MERCHANT, depth=0, path=m.id,
                sells=False, loyalty_domain_id=m.id, settlement_account_id=m.id,
                is_settlement_boundary=True, is_loyalty_domain=True, is_active=m.is_active)
        counts["merchant"] += 1

    for b in db.scalars(select(Brand)).all():
        _upsert(db, node_id=b.id, parent_id=b.merchant_id, role=ROLE_BRAND, depth=1,
                path=PATH_SEP.join([b.merchant_id, b.id]),
                sells=False, loyalty_domain_id=b.merchant_id, settlement_account_id=b.merchant_id,
                is_settlement_boundary=False, is_loyalty_domain=False, is_active=b.is_active)
        counts["brand"] += 1

    for o in db.scalars(select(Outlet)).all():
        _upsert(db, node_id=o.id, parent_id=o.brand_id, role=ROLE_OUTLET, depth=2,
                path=PATH_SEP.join([o.merchant_id, o.brand_id, o.id]),
                sells=False, loyalty_domain_id=o.merchant_id, settlement_account_id=o.merchant_id,
                is_settlement_boundary=False, is_loyalty_domain=False, is_active=o.is_active)
        counts["outlet"] += 1

    # Menus = stalls (the orderable leaves). Parent is the outlet.
    for menu in db.scalars(select(Menu)).all():
        outlet = db.get(Outlet, menu.outlet_id)
        if outlet is None:
            continue
        _upsert(db, node_id=menu.id, parent_id=menu.outlet_id, role=ROLE_STALL, depth=3,
                path=PATH_SEP.join([menu.merchant_id, outlet.brand_id, menu.outlet_id, menu.id]),
                sells=True, loyalty_domain_id=menu.merchant_id, settlement_account_id=menu.merchant_id,
                is_settlement_boundary=False, is_loyalty_domain=False, is_active=menu.is_active)
        counts["stall"] += 1

    db.flush()
    return counts


# ---- queries (path-prefix, no recursion) ----------------------------------
def node_for(db: Session, entity_id: str) -> OrgNode | None:
    return db.get(OrgNode, entity_id)


def _subtree_filter(path: str):
    """Node at `path` plus every descendant (`path.%`)."""
    return or_(OrgNode.path == path, OrgNode.path.like(path + PATH_SEP + "%"))


def subtree(db: Session, node: OrgNode, *, active_only: bool = True) -> list[OrgNode]:
    stmt = select(OrgNode).where(_subtree_filter(node.path))
    if active_only:
        stmt = stmt.where(OrgNode.is_active.is_(True))
    return list(db.scalars(stmt.order_by(OrgNode.depth, OrgNode.id)).all())


def sellable_under(db: Session, node: OrgNode, *, active_only: bool = True) -> list[OrgNode]:
    """Sellable endpoints (stalls/storefronts) in this node's subtree, incl. the node itself
    if it sells. This is the QR/app/POS resolution primitive."""
    stmt = select(OrgNode).where(_subtree_filter(node.path), OrgNode.sells.is_(True))
    if active_only:
        stmt = stmt.where(OrgNode.is_active.is_(True))
    return list(db.scalars(stmt.order_by(OrgNode.path)).all())
