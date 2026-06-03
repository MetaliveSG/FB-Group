"""Org-structure admin routes: brands / outlets / tables + QR (Module 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.auth.permissions import P, WILDCARD
from app.db.session import get_db
from app.models.tenancy import Merchant
from app.schemas.org import (
    BrandCreateIn,
    BrandOut,
    BrandUpdateIn,
    LeaseCreateIn,
    LeaseOut,
    LeaseUpdateIn,
    LoyaltyProgramOut,
    LoyaltyProgramUpdateIn,
    MyPermissionsOut,
    NavFlagsOut,
    NodeAccountCreateIn,
    NodeAccountOut,
    OrgNodeCreateIn,
    OrgNodeOut,
    OrgNodeUpdateIn,
    OrgTreeOut,
    OutletCreateIn,
    OutletOut,
    OutletUpdateIn,
    SettingsOut,
    SettingsUpdateIn,
    TableCreateIn,
    TableOut,
)
from app.services import (
    leasing,
    loyalty_admin,
    merchant_settings,
    org_admin,
    org_tree,
    storefronts,
    users_admin,
)
from app.services.audit import record as audit_record

router = APIRouter(prefix="/org", tags=["org"])


def _mid(scope, merchant_id, perm):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, perm, mid)
    return mid


# --- Merchant settings (feature toggles) ---
# Nav flags: the non-sensitive boolean subset (no spin costs / earn rates) every staff
# member may read to render navigation. `order.view` is the universal floor (staff, outlet
# manager, brand manager, owner all hold it). Full /settings + /loyalty are owner-only below,
# so a downline manager cannot read merchant-level economic config — only what nav needs.
_ALL_PERMS = sorted(P.keys())  # every defined permission code (wildcard expansion target)


@router.get("/permissions", response_model=MyPermissionsOut)
def my_permissions(merchant_id: str | None = Query(None), scope=Depends(get_scope)):
    """Caller's effective permissions in a merchant context — the capabilities contract for
    client nav-gating. Server still enforces per-route; this only prunes the menu."""
    # Super admin (operator) holds the wildcard everywhere → expand to the full set so the
    # client can do a simple `permissions.includes(x)` without special-casing '*'.
    if scope.is_super_admin:
        return MyPermissionsOut(permissions=_ALL_PERMS, is_super_admin=True)
    if merchant_id is None and len(scope.accessible_merchant_ids) != 1:
        # Enterprise (multi-merchant) account with no merchant chosen, or none at all: return the
        # UNION of what the caller can do anywhere so the console chrome (nav) renders. Per-route
        # handlers still re-check against a concrete merchant — this only prunes the menu.
        perms: set[str] = set()
        for m in scope.accessible_merchant_ids:
            perms |= scope.effective_permissions(m)
    else:
        mid = resolve_merchant(scope, merchant_id)  # also enforces the caller belongs to it
        perms = scope.effective_permissions(mid)
    if WILDCARD in perms:  # defensive — non-super shouldn't hold it, but expand if so
        return MyPermissionsOut(permissions=_ALL_PERMS, is_super_admin=True)
    return MyPermissionsOut(permissions=sorted(perms), is_super_admin=False)


# --- Org tree (member-tree spine) — build the hierarchy at ANY depth -------
# These endpoints are scope-aware and need NO merchant_id: they key off the caller's org-node
# assignments (see Scope.node_ids / manage_node_ids), so an Enterprise account sees the whole
# group while a Brand/Outlet manager sees only its own subtree — downline-only, never upline.
def _node_out(node, can_manage: bool, qr_path: str | None = None,
              outlet_id: str | None = None) -> OrgNodeOut:
    return OrgNodeOut(id=node.id, parent_id=node.parent_id, role=node.role, name=node.name,
                      depth=node.depth, sells=node.sells, chain_stopped=node.chain_stopped,
                      is_settlement_boundary=node.is_settlement_boundary,
                      subscription_fee=node.subscription_fee, is_active=node.is_active,
                      can_manage=can_manage, qr_path=qr_path, outlet_id=outlet_id)


def _qr_paths_for(db, nodes) -> dict[str, str]:
    """The 'QR Menu' link per node — always the node's OWN stalls (never another owner's venue).
    A **Storefront** → `/t/{token}` of ITS OWN outlet (full table-QR ordering); node-keyed via
    menu.id==node.id → outlet → token, so each storefront of a chain opens its own venue (not the
    tenant's first one). Anything else with orderable leaves in its own scope (a tenant, or a real
    multi-stall group) → a node-scoped browse `/t/node/{id}`. None where nothing is orderable."""
    from app.models.catalog import Menu
    from app.models.tenancy import QRCode
    from app.services import catalog as catalog_service

    # First stable token per outlet + per merchant; and each sellable node's own outlet
    # (menu.id == node.id). A chain Storefront resolves to its OWN outlet's token; a collapsed
    # single-storefront merchant (node.id == merchant.id, menus under their own ids) has no
    # node-own outlet, so it falls back to the merchant's first token.
    outlet_token: dict[str, str] = {}
    merchant_token: dict[str, str] = {}
    for mid, oid, token in db.execute(
        select(QRCode.merchant_id, QRCode.outlet_id, QRCode.token).order_by(QRCode.token)
    ).all():
        outlet_token.setdefault(oid, token)
        merchant_token.setdefault(mid, token)
    menu_outlet = dict(db.execute(select(Menu.id, Menu.outlet_id)).all())

    paths: dict[str, str] = {}
    for n in nodes:
        own_token = outlet_token.get(menu_outlet.get(n.id)) or (
            merchant_token.get(n.settlement_account_id) if n.sells else None)
        if n.sells and own_token:
            paths[n.id] = f"/t/{own_token}"                 # this storefront's own table QR → full scan
        elif catalog_service.node_scope_stalls(db, n):
            paths[n.id] = f"/t/node/{n.id}"                 # browse its own stalls (group/brand app)
    return paths


@router.get("/tree", response_model=OrgTreeOut)
def get_org_tree(scope=Depends(get_scope), db: Session = Depends(get_db)):
    """The caller's visible slice of the member-tree (flat; client assembles via parent_id).
    Each node carries `can_manage` (may grow the tree here) + `qr_path` (a customer-scan link)."""
    from app.models.catalog import Menu
    nodes = org_tree.visible_nodes(db, scope)
    paths = _qr_paths_for(db, nodes)
    # A Storefront's typed Outlet (menu.id == node.id → menu.outlet_id) so the console can scope to it.
    menu_outlet = dict(db.execute(select(Menu.id, Menu.outlet_id)).all())
    out = [
        _node_out(n, org_tree.can_manage_node(db, scope, n), paths.get(n.id),
                  menu_outlet.get(n.id) if n.sells else None)
        for n in nodes
    ]
    return OrgTreeOut(nodes=out, can_manage=any(n.can_manage for n in out))


@router.post("/nodes", response_model=OrgNodeOut, status_code=201)
def create_org_node(body: OrgNodeCreateIn, scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Create a child node under a parent the caller manages — any depth (enterprise→stall)."""
    parent = org_tree.get_managed_node(db, scope, body.parent_id)  # 404 absent / 403 upline
    node = org_tree.create_child(db, parent=parent, role=body.role, name=body.name,
                                 chain_stopped=body.chain_stopped,
                                 subscription_fee=body.subscription_fee)
    # A Storefront sells — give it its typed backing (outlet + menu(id==node.id) + QR token) so it
    # is immediately scannable/orderable and shows a "QR Menu" + a real outlet in the merchant console.
    if node.sells:
        storefronts.provision_storefront(db, node)
    # merchant_id left unset: a node's settlement account may be a pure-spine id with no typed
    # Merchant row (the audit_logs FK requires a real merchant or NULL) — captured in meta.
    audit_record(db, action="org.node_create", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=node.id,
                 meta={"role": node.role, "name": node.name, "parent_id": parent.id,
                       "settlement_account_id": node.settlement_account_id})
    db.commit()
    return _node_out(node, can_manage=True)


@router.patch("/nodes/{node_id}", response_model=OrgNodeOut)
def update_org_node(node_id: str, body: OrgNodeUpdateIn, scope=Depends(get_scope),
                    db: Session = Depends(get_db)):
    """Rename / (de)activate a node the caller manages."""
    node = org_tree.get_managed_node(db, scope, node_id)  # 404 absent / 403 upline
    if body.name is not None:
        node.name = body.name.strip()
    if body.is_active is not None:
        node.is_active = body.is_active
        # Single status: a tenant node mirrors its active state onto the typed Merchant, so the
        # one toggle is the source of truth (no second, divergent merchant flag to manage).
        if node.is_settlement_boundary:
            m = db.get(Merchant, node.settlement_account_id)
            if m is not None:
                m.is_active = body.is_active
    if body.chain_stopped is not None and not node.sells:  # no-op on a Storefront (it has no children)
        node.chain_stopped = body.chain_stopped
    if body.subscription_fee is not None:
        node.subscription_fee = body.subscription_fee
    audit_record(db, action="org.node_update", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=node.id,
                 meta={**body.model_dump(exclude_none=True, mode="json"),
                       "settlement_account_id": node.settlement_account_id})
    db.commit()
    return _node_out(node, can_manage=True)


# --- Node logins — staff assigned at a member-tree node (manager/cashier/staff/finance) ----
@router.get("/nodes/{node_id}/accounts", response_model=list[NodeAccountOut])
def list_node_accounts(node_id: str, scope=Depends(get_scope), db: Session = Depends(get_db)):
    org_tree.get_managed_node(db, scope, node_id)             # 404 absent / 403 outside downline
    return users_admin.list_node_accounts(db, node_id=node_id)


@router.post("/nodes/{node_id}/accounts", response_model=NodeAccountOut, status_code=201)
def create_node_account(node_id: str, body: NodeAccountCreateIn,
                        scope=Depends(get_scope), db: Session = Depends(get_db)):
    org_tree.get_managed_node(db, scope, node_id)
    acct = users_admin.create_node_account(db, node_id=node_id, email=body.email,
                                           password=body.password, full_name=body.full_name, role=body.role)
    audit_record(db, action="org.node_account_create", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=node_id,
                 meta={"email": body.email, "role": body.role})
    db.commit()
    return acct


@router.delete("/nodes/{node_id}/accounts/{assignment_id}", status_code=204)
def revoke_node_account(node_id: str, assignment_id: str,
                        scope=Depends(get_scope), db: Session = Depends(get_db)):
    org_tree.get_managed_node(db, scope, node_id)
    users_admin.revoke_node_account(db, node_id=node_id, assignment_id=assignment_id)
    audit_record(db, action="org.node_account_revoke", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=node_id, meta={"assignment_id": assignment_id})
    db.commit()


# --- Leases — stalls leased INTO a venue (foodcourt GTO vs coffeeshop FIXED) ----
# Managed from the VENUE node's drawer: `rent_type` is the only switch (FIXED = flat rent, landlord
# blind; GTO = % of turnover, landlord reads it). Gated on managing the venue (get_managed_node).
def _lease_out(db, lease) -> LeaseOut:
    tnode = org_tree.node_for(db, lease.tenant_node_id)
    return LeaseOut(id=lease.id, venue_id=lease.venue_id, tenant_node_id=lease.tenant_node_id,
                    tenant_name=(tnode.name if tnode else None), rent_type=lease.rent_type,
                    rate=lease.rate, is_active=lease.is_active)


@router.get("/nodes/{node_id}/leases", response_model=list[LeaseOut])
def list_venue_leases(node_id: str, scope=Depends(get_scope), db: Session = Depends(get_db)):
    venue = org_tree.get_managed_node(db, scope, node_id)         # 404 absent / 403 outside downline
    return [_lease_out(db, ls) for ls in leasing.list_leases_for_venue(db, venue)]


@router.post("/nodes/{node_id}/leases", response_model=LeaseOut, status_code=201)
def create_venue_lease(node_id: str, body: LeaseCreateIn,
                       scope=Depends(get_scope), db: Session = Depends(get_db)):
    venue = org_tree.get_managed_node(db, scope, node_id)
    lease = leasing.create_lease(db, venue=venue, tenant_node_id=body.tenant_node_id,
                                 rent_type=body.rent_type, rate=body.rate)
    audit_record(db, action="org.lease_create", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=venue.id,
                 meta={"tenant_node_id": body.tenant_node_id, "rent_type": lease.rent_type,
                       "rate": str(lease.rate)})
    db.commit()
    return _lease_out(db, lease)


@router.patch("/nodes/{node_id}/leases/{lease_id}", response_model=LeaseOut)
def update_venue_lease(node_id: str, lease_id: str, body: LeaseUpdateIn,
                       scope=Depends(get_scope), db: Session = Depends(get_db)):
    venue = org_tree.get_managed_node(db, scope, node_id)
    lease = leasing.get_venue_lease(db, venue, lease_id)
    leasing.update_lease(db, lease=lease, rent_type=body.rent_type, rate=body.rate,
                         is_active=body.is_active)
    audit_record(db, action="org.lease_update", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=venue.id,
                 meta={"lease_id": lease_id, **body.model_dump(exclude_none=True, mode="json")})
    db.commit()
    return _lease_out(db, lease)


@router.delete("/nodes/{node_id}/leases/{lease_id}", status_code=204)
def delete_venue_lease(node_id: str, lease_id: str,
                       scope=Depends(get_scope), db: Session = Depends(get_db)):
    venue = org_tree.get_managed_node(db, scope, node_id)
    lease = leasing.get_venue_lease(db, venue, lease_id)
    leasing.delete_lease(db, lease)
    audit_record(db, action="org.lease_delete", actor_id=scope.user_id,
                 entity_type="org_node", entity_id=venue.id, meta={"lease_id": lease_id})
    db.commit()


@router.get("/nav-flags", response_model=NavFlagsOut)
def get_nav_flags(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "order.view")
    flags = merchant_settings.get_nav_flags(db, merchant_id=mid)
    # Capability for client nav-gating: whether the caller may manage merchant-level config
    # (true for the owner + an operator drilled into the merchant). Lets the UI hide
    # owner-only nav without exposing the settings themselves.
    return {**flags, "can_manage_merchant": scope.can("merchant.manage", mid)}


@router.get("/settings", response_model=SettingsOut)
def get_settings(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")  # owner-only — hard upline isolation
    return merchant_settings.get_settings(db, merchant_id=mid)


@router.patch("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdateIn, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")
    out = merchant_settings.update_settings(db, merchant_id=mid, changes=body.model_dump(exclude_none=True))
    audit_record(db, action="merchant.settings_update", actor_id=scope.user_id, merchant_id=mid,
                 meta=body.model_dump(exclude_none=True))
    db.commit()
    return out


# --- Loyalty program (standing earn rules: earn rate / welcome / birthday) ---
@router.get("/loyalty", response_model=LoyaltyProgramOut)
def get_loyalty_program(merchant_id: str | None = Query(None), scope=Depends(get_scope),
                        db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")  # owner-only — earn rates are upline config
    return loyalty_admin.get_program(db, merchant_id=mid)


@router.put("/loyalty", response_model=LoyaltyProgramOut)
def update_loyalty_program(body: LoyaltyProgramUpdateIn, merchant_id: str | None = Query(None),
                           scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")
    out = loyalty_admin.update_program(
        db, merchant_id=mid, points_per_dollar=body.points_per_dollar,
        welcome_bonus=body.welcome_bonus, birthday_bonus=body.birthday_bonus,
    )
    audit_record(db, action="merchant.loyalty_update", actor_id=scope.user_id, merchant_id=mid,
                 meta=body.model_dump())
    db.commit()
    return out


# --- Brands ---
@router.get("/brands", response_model=list[BrandOut])
def list_brands(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    return org_admin.list_brands(db, merchant_id=mid)


@router.post("/brands", response_model=BrandOut, status_code=201)
def create_brand(body: BrandCreateIn, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "brand.manage")
    b = org_admin.create_brand(db, merchant_id=mid, name=body.name, cuisine_type=body.cuisine_type)
    audit_record(db, action="org.brand_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="brand", entity_id=b.id)
    db.commit()
    return BrandOut(id=b.id, name=b.name, cuisine_type=b.cuisine_type, is_active=b.is_active, outlets=0)


@router.patch("/brands/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: str, body: BrandUpdateIn, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "brand.manage")
    org_admin.update_brand(db, merchant_id=mid, brand_id=brand_id, name=body.name,
                           cuisine_type=body.cuisine_type, is_active=body.is_active)
    db.commit()
    return next(b for b in org_admin.list_brands(db, merchant_id=mid) if b["id"] == brand_id)


# --- Outlets ---
@router.get("/outlets", response_model=list[OutletOut])
def list_outlets(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    return org_admin.list_outlets(db, merchant_id=mid)


@router.post("/outlets", response_model=OutletOut, status_code=201)
def create_outlet(body: OutletCreateIn, merchant_id: str | None = Query(None),
                  scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    o = org_admin.create_outlet(db, merchant_id=mid, brand_id=body.brand_id, name=body.name, address=body.address)
    audit_record(db, action="org.outlet_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="outlet", entity_id=o.id)
    db.commit()
    return next(x for x in org_admin.list_outlets(db, merchant_id=mid) if x["id"] == o.id)


@router.patch("/outlets/{outlet_id}", response_model=OutletOut)
def update_outlet(outlet_id: str, body: OutletUpdateIn, merchant_id: str | None = Query(None),
                  scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    org_admin.update_outlet(db, merchant_id=mid, outlet_id=outlet_id, name=body.name,
                            address=body.address, is_active=body.is_active)
    db.commit()
    return next(x for x in org_admin.list_outlets(db, merchant_id=mid) if x["id"] == outlet_id)


# --- Tables + QR ---
@router.get("/outlets/{outlet_id}/tables", response_model=list[TableOut])
def list_tables(outlet_id: str, merchant_id: str | None = Query(None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    return org_admin.list_tables(db, merchant_id=mid, outlet_id=outlet_id)


@router.post("/outlets/{outlet_id}/tables", response_model=TableOut, status_code=201)
def create_table(outlet_id: str, body: TableCreateIn, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    row = org_admin.create_table(db, merchant_id=mid, outlet_id=outlet_id, label=body.label, seats=body.seats)
    audit_record(db, action="org.table_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="table", entity_id=row["id"])
    db.commit()
    return TableOut(**row)


@router.delete("/tables/{table_id}", status_code=204)
def delete_table(table_id: str, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    org_admin.delete_table(db, merchant_id=mid, table_id=table_id)
    db.commit()
