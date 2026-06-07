"""Build & query the org spine (`org_nodes`) — the member-tree-map.

`sync_org_tree` keeps the spine in sync with the typed tables (Merchant/Brand/Outlet/Menu),
idempotently (upsert keyed by id, like the seed bolt-ons). It is the single place that derives
`path`/`depth`/flags, so the tree invariants live in one function. Read paths use the path-prefix
helpers (`sellable_under`, `subtree`) instead of recursive walks.

Today the tree is the fixed chain merchant → brand → outlet → stall(menu); the *shape* is
generic (adjacency + path), so deeper/ragged trees are an additive change later.
"""
from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.models.catalog import Menu
from app.models.org import PATH_SEP, OrgNode
from app.models.tenancy import Brand, Merchant, Outlet

# The member tree has exactly two node KINDS (the engine keys off the `sells` flag, not the label):
#   CHAIN      — structural container; may hold Chain or Storefront children (unless chain_stopped).
#   STOREFRONT — the only node that SELLS (has a menu / takes orders); a hard leaf, no children.
ROLE_CHAIN = "CHAIN"
ROLE_STOREFRONT = "STOREFRONT"
NODE_ROLES = (ROLE_CHAIN, ROLE_STOREFRONT)


def _upsert(db: Session, *, node_id: str, parent_id: str | None, role: str, depth: int,
            path: str, sells: bool, loyalty_domain_id: str, settlement_account_id: str,
            is_settlement_boundary: bool, is_loyalty_domain: bool, is_active: bool,
            name: str | None = None) -> OrgNode:
    node = db.get(OrgNode, node_id)
    if node is None:
        node = OrgNode(id=node_id)
        db.add(node)
    node.parent_id = parent_id
    node.role = role
    node.name = name
    node.depth = depth
    node.path = path
    node.sells = sells
    node.loyalty_domain_id = loyalty_domain_id
    node.settlement_account_id = settlement_account_id
    node.is_settlement_boundary = is_settlement_boundary
    node.is_loyalty_domain = is_loyalty_domain
    node.is_active = is_active
    return node


def _member_kind(m: Merchant) -> str:
    """'storefront' = a simple single-storefront business (collapsed: the merchant IS the
    storefront, no brand/outlet/menu shown in the member tree); else 'chain' (full structure)."""
    return (m.settings or {}).get("member_kind", "chain")


def sync_org_tree(db: Session) -> dict:
    """Idempotently mirror the typed tables into the spine (Chain/Storefront). Safe to re-run.
    A merchant flagged `member_kind=storefront` collapses to ONE Storefront node — its typed
    brand/outlet/menu still exist (for ordering) but are skipped + pruned from the spine, so it
    shows as a single storefront at the top level. Unflagged merchants build the full Chain tree."""
    counts = {"merchant": 0, "brand": 0, "outlet": 0, "stall": 0}

    storefront_mids: set[str] = set()
    for m in db.scalars(select(Merchant)).all():
        if _member_kind(m) == "storefront":
            storefront_mids.add(m.id)
            # The merchant IS the storefront (sells, its own tenant) — a leaf.
            _upsert(db, node_id=m.id, parent_id=None, role=ROLE_STOREFRONT, depth=0, path=m.id,
                    name=m.name, sells=True, loyalty_domain_id=m.id, settlement_account_id=m.id,
                    is_settlement_boundary=True, is_loyalty_domain=True, is_active=m.is_active)
            # Prune any spine children left from a prior Chain shape (leaves-first).
            for stale in db.scalars(
                select(OrgNode).where(OrgNode.path.like(m.id + PATH_SEP + "%"))
                .order_by(OrgNode.depth.desc())
            ).all():
                db.delete(stale)
        else:
            _upsert(db, node_id=m.id, parent_id=None, role=ROLE_CHAIN, depth=0, path=m.id,
                    name=m.name, sells=False, loyalty_domain_id=m.id, settlement_account_id=m.id,
                    is_settlement_boundary=True, is_loyalty_domain=True, is_active=m.is_active)
        counts["merchant"] += 1
    db.flush()

    for b in db.scalars(select(Brand)).all():
        if b.merchant_id in storefront_mids:
            continue                                              # collapsed merchant — no spine child
        _upsert(db, node_id=b.id, parent_id=b.merchant_id, role=ROLE_CHAIN, depth=1,
                path=PATH_SEP.join([b.merchant_id, b.id]), name=b.name,
                sells=False, loyalty_domain_id=b.merchant_id, settlement_account_id=b.merchant_id,
                is_settlement_boundary=False, is_loyalty_domain=False, is_active=b.is_active)
        counts["brand"] += 1

    for o in db.scalars(select(Outlet)).all():
        if o.merchant_id in storefront_mids:
            continue
        _upsert(db, node_id=o.id, parent_id=o.brand_id, role=ROLE_CHAIN, depth=2,
                path=PATH_SEP.join([o.merchant_id, o.brand_id, o.id]), name=o.name,
                sells=False, loyalty_domain_id=o.merchant_id, settlement_account_id=o.merchant_id,
                is_settlement_boundary=False, is_loyalty_domain=False, is_active=o.is_active)
        counts["outlet"] += 1

    # Menus = the orderable leaves → Storefronts. Parent is the outlet.
    for menu in db.scalars(select(Menu)).all():
        if menu.merchant_id in storefront_mids:
            continue
        outlet = db.get(Outlet, menu.outlet_id)
        if outlet is None:
            continue
        _upsert(db, node_id=menu.id, parent_id=menu.outlet_id, role=ROLE_STOREFRONT, depth=3,
                path=PATH_SEP.join([menu.merchant_id, outlet.brand_id, menu.outlet_id, menu.id]),
                name=menu.name,
                sells=True, loyalty_domain_id=menu.merchant_id, settlement_account_id=menu.merchant_id,
                is_settlement_boundary=False, is_loyalty_domain=False, is_active=menu.is_active)
        counts["stall"] += 1

    db.flush()
    return counts


# ---- queries (path-prefix, no recursion) ----------------------------------
def node_for(db: Session, entity_id: str) -> OrgNode | None:
    return db.get(OrgNode, entity_id)


def is_live(db: Session, node: OrgNode) -> bool:
    """True iff the node AND all its ancestors are active — suspend CASCADES down the tree
    (suspending a Chain effectively suspends every Storefront beneath it). `node.path` is the
    PATH_SEP-joined chain of ancestor ids (incl. self)."""
    ancestor_ids = node.path.split(PATH_SEP)
    suspended = db.scalar(
        select(OrgNode.id).where(OrgNode.id.in_(ancestor_ids), OrgNode.is_active.is_(False)).limit(1)
    )
    return suspended is None


def _subtree_filter(path: str):
    """Node at `path` plus every descendant (`path.%`)."""
    return or_(OrgNode.path == path, OrgNode.path.like(path + PATH_SEP + "%"))


def node_in_subtree(db: Session, *, ancestor_id: str, node_id: str) -> bool:
    """True iff `node_id` is `ancestor_id` or a descendant of it (voucher scope = subtree reach)."""
    if ancestor_id == node_id:
        return True
    anc = db.get(OrgNode, ancestor_id)
    node = db.get(OrgNode, node_id)
    if anc is None or node is None:
        return False
    return node.path == anc.path or node.path.startswith(anc.path + PATH_SEP)


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


def grants_for_node(db: Session, node: OrgNode) -> list[tuple[str, set[str] | None]]:
    """RBAC cascade for a role assigned at ANY node: returns (tenant_id, limit) grants over the
    node's subtree. `limit=None` means ALL (the whole tenant). FLAG-based, not role labels.
    - If the subtree contains **settlement boundaries** (tenant nodes) → grant each, whole. A node
      above several tenants (a group Chain) thus spans every tenant beneath it.
    - Else the node sits *within* one tenant → grant that tenant (the node's `settlement_account_id`),
      limited to the sellable endpoints in its subtree (typed outlets where present, else the
      Storefront node ids; a Storefront scopes to itself).
    Cross-tenant-safe by construction (path-prefix); any depth, no recursion.
    """
    boundaries = [n for n in subtree(db, node, active_only=False) if n.is_settlement_boundary]
    if boundaries:
        return [(b.id, None) for b in boundaries]
    # A Storefront scopes to its own typed outlet; a Chain to the outlets in its subtree. Orders are
    # tagged by OUTLET id, so resolve the real outlet (provisioned: menu.id==node.id→outlet, separate
    # uuid) via outlet_ids_under; fall back to node ids only for pure-spine/legacy (outlet.id==node.id).
    limit: set[str] = outlet_ids_under(db, node)
    if not limit:
        limit = {node.id} if node.sells else {n.id for n in sellable_under(db, node, active_only=False)}
    return [(node.settlement_account_id, limit)]


def outlet_ids_under(db: Session, node: OrgNode) -> set[str]:
    """Typed **Outlet** ids in a node's subtree — the legacy RBAC limit unit (orders/customers are
    tagged by outlet_id). Resolved by subtree membership, not by a role label, so it survives the
    Chain/Storefront relabel: a role scoped to a merchant/brand reaches exactly the outlets beneath
    it. Cross-tenant-safe (a different tenant's outlets have a different path prefix); empty for a
    pure-spine subtree with no typed outlets (e.g. a seeded enterprise) — caller falls back to the
    Storefront node ids.
    """
    subtree_ids = select(OrgNode.id).where(_subtree_filter(node.path), OrgNode.is_active.is_(True))
    # Two node→outlet mappings coexist: legacy/collapsed where Outlet.id == node.id, and PROVISIONED
    # storefronts where the link is Menu.id == node.id → Menu.outlet_id (a separate uuid outlet). Union
    # both so node-scoped staff (POS operators, storefront managers) reach their real outlet.
    ids = set(db.scalars(select(Outlet.id).where(Outlet.id.in_(subtree_ids))).all())
    ids |= set(db.scalars(select(Menu.outlet_id).where(Menu.id.in_(subtree_ids))).all())
    return ids


# ---- org-tree management (build the member-tree, any depth) ----------------
def visible_nodes(db: Session, scope) -> list[OrgNode]:
    """Every org node the caller may SEE — depth-agnostic, downline-only.

    A platform operator who can see the merchant directory → the whole forest (the operator
    console drills the member-tree). Otherwise the union of the subtrees of the nodes the caller
    is assigned at (`scope.node_ids`): a role at a node sees its node and everything beneath it,
    never a sibling or an ancestor. De-duplicated when assignments nest.
    """
    platform_perms = getattr(scope, "platform_perms", set())
    sees_all = (
        getattr(scope, "is_super_admin", False)
        or getattr(scope, "platform_drilldown", None)
        or "platform.merchants.view" in platform_perms
    )
    if sees_all:
        return list(db.scalars(select(OrgNode).order_by(OrgNode.path)).all())
    seen: dict[str, OrgNode] = {}
    for nid in sorted(scope.node_ids):
        root = db.get(OrgNode, nid)
        if root is None:
            continue
        for n in subtree(db, root, active_only=False):
            seen[n.id] = n
    return sorted(seen.values(), key=lambda n: n.path)


def _manage_roots(db: Session, scope) -> list[OrgNode]:
    return [n for n in (db.get(OrgNode, nid) for nid in scope.manage_node_ids) if n is not None]


def can_manage_node(db: Session, scope, node: OrgNode) -> bool:
    """May the caller create/rename under `node`? True iff `node` lies within (at or below) a
    node the caller is assigned at WITH `org.manage` — strictly downline, never upline/sibling."""
    if getattr(scope, "is_super_admin", False):
        return True
    for root in _manage_roots(db, scope):
        if node.path == root.path or node.path.startswith(root.path + PATH_SEP):
            return True
    return False


def create_child(db: Session, *, parent: OrgNode, role: str, name: str,
                 chain_stopped: bool = False, subscription_fee=None) -> OrgNode:
    """Create a child node under `parent`, deriving path/depth/flags. Enforces the model:
    - the parent must be a **Chain** — a Storefront is a hard leaf, nothing attaches under it;
    - if the parent has **stopped the chain**, the child may only be a Storefront (no sub-Chains);
    - `sells = (kind == STOREFRONT)` — only a Storefront sells / gets a menu.
    Boundary pointers inherit the parent's (a new node is not itself a tenant; promoting a Chain to
    a settlement boundary is a separate action). `subscription_fee` is per-node (NULL = inherit).
    """
    role = (role or "").upper()
    if role not in NODE_ROLES:
        raise AppError(f"Unknown node kind: {role!r} (use CHAIN or STOREFRONT)", code="bad_kind",
                       status_code=400)
    if parent.sells:
        raise AppError("A Storefront is a leaf — it cannot have children", code="leaf_parent",
                       status_code=400)
    if parent.chain_stopped and role == ROLE_CHAIN:
        raise AppError("This Chain is stopped — children may only be Storefronts",
                       code="chain_stopped", status_code=400)
    name = (name or "").strip()
    if not name:
        raise AppError("name is required", code="name_required", status_code=400)
    nid = uuid.uuid4().hex
    node = OrgNode(
        id=nid, parent_id=parent.id, role=role, name=name,
        depth=parent.depth + 1, path=PATH_SEP.join([parent.path, nid]),
        sells=(role == ROLE_STOREFRONT),
        is_settlement_boundary=False, is_loyalty_domain=False,
        loyalty_domain_id=parent.loyalty_domain_id,
        settlement_account_id=parent.settlement_account_id,
        chain_stopped=bool(chain_stopped) if role == ROLE_CHAIN else False,
        subscription_fee=subscription_fee,
        is_active=True,
    )
    db.add(node)
    db.flush()
    return node


def get_managed_node(db: Session, scope, node_id: str) -> OrgNode:
    """Fetch a node the caller may manage, or raise (404 if absent, 403 if outside the downline)."""
    node = db.get(OrgNode, node_id)
    if node is None:
        raise NotFoundError("Node not found", code="node_not_found")
    if not can_manage_node(db, scope, node):
        raise ForbiddenError("No access to this node", code="forbidden")
    return node
