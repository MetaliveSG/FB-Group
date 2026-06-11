"""Public QR resolution -> dining context + outlet menu (no auth, no app download)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.org import OrgNode
from app.models.tenancy import Brand, DiningTable, Merchant, Outlet
from app.core.errors import NotFoundError
from app.schemas.catalog import MenuOut
from app.schemas.qr import NodeBrowseOut, ParentGroupRef, QrContextOut, StallRef
from app.services import boundaries
from app.services import catalog as catalog_service
from app.services import i18n
from app.services import org_tree
from app.services import qr as qr_service

router = APIRouter(prefix="/qr", tags=["qr"])


def _tenant_default_locale(merchant: Merchant | None) -> str | None:
    return (merchant.settings or {}).get("locale") if merchant else None


def _service_options_for(db: Session, outlet_id: str) -> list[dict]:
    """The storefront's enabled service options (cascade-resolved) as {key, label, hand_off, order_type}
    for the diner's picker. Preserves the configured order; defaults to restaurant table service."""
    from app.models.enums import SERVICE_OPTIONS
    keys = boundaries.resolve_service_options_for_outlet(db, outlet_id=outlet_id)
    return [{"key": k, **SERVICE_OPTIONS[k]} for k in keys if k in SERVICE_OPTIONS]


@router.get("/{token}", response_model=QrContextOut)
def resolve_qr(
    token: str,
    db: Session = Depends(get_db),
    lang: str | None = Query(default=None),
    accept_language: str | None = Header(default=None),
):
    qr = qr_service.resolve_token(db, token)
    merchant = db.get(Merchant, qr.merchant_id)
    outlet = db.get(Outlet, qr.outlet_id)
    brand = db.get(Brand, outlet.brand_id)
    table = db.get(DiningTable, qr.table_id)
    locale = i18n.resolve_locale(override=lang, tenant_default=_tenant_default_locale(merchant),
                                 accept_language=accept_language)

    # An outlet may host many stalls (menus). One → restaurant (inline menu, backward
    # compat); many → foodcourt (stall directory, fetch a menu on tap). The sellable set is
    # resolved through the org spine (Phase 1b); behaviour-identical for the current tree.
    menus = catalog_service.list_outlet_stalls(db, qr.outlet_id)
    is_foodcourt = len(menus) > 1
    stalls = [
        StallRef(
            menu_id=m.id,
            stall_name=m.stall_name or m.name,
            cuisine=m.cuisine,
            logo=m.logo,
            is_open=m.is_open,
            item_count=catalog_service.menu_item_count(db, m.id),
        )
        for m in menus
    ]
    flags = boundaries.resolve_modules_for_outlet(db, outlet_id=qr.outlet_id, merchant_id=qr.merchant_id)
    # Suspend: a suspended tenant shows as "ordering unavailable" (graceful) — the order endpoint also
    # hard-blocks, and storefront/chain-level suspend is enforced per-stall at order time.
    ordering_enabled = flags["qr_ordering_enabled"] and merchant.is_active
    inline_menu = None
    if ordering_enabled and not is_foodcourt and menus:
        full = catalog_service.get_outlet_menu(db, qr.outlet_id, menus[0].id)
        inline_menu = MenuOut.model_validate(i18n.localize_menu(full, locale))

    # If this single stall sits under a multi-stall group (foodcourt), let the diner pop up and switch
    # stalls. Resolved from the stall's OWN node (menu.id == node.id) → its direct parent → sibling count,
    # so it works even on a direct stall scan, not only when navigated in from the group browse.
    parent_group = None
    if not is_foodcourt and menus:
        sf_node = db.get(OrgNode, menus[0].id)
        if sf_node and sf_node.parent_id:
            parent = db.get(OrgNode, sf_node.parent_id)
            if parent is not None and not parent.sells:
                siblings = catalog_service.direct_storefronts(db, parent)
                if len(siblings) > 1:
                    parent_group = ParentGroupRef(node_id=parent.id, name=parent.name or parent.id,
                                                  stall_count=len(siblings))

    return QrContextOut(
        qr_token=qr.token,
        merchant={"id": merchant.id, "name": merchant.name},
        brand={"id": brand.id, "name": brand.name},
        outlet={"id": outlet.id, "name": outlet.name, "address": outlet.address},
        table={"id": table.id, "label": table.label},
        is_foodcourt=is_foodcourt,
        stalls=stalls,
        menu=inline_menu,
        ordering_enabled=ordering_enabled,
        rewards_enabled=flags["rewards_enabled"],
        service_options=_service_options_for(db, qr.outlet_id),
        theme=boundaries.resolve_theme_for_outlet(db, outlet_id=qr.outlet_id),
        locale=locale,
        currency=(merchant.currency if merchant else "SGD"),
        parent_group=parent_group,
    )


# --- Node-scoped browse ("brand / group app"): point at ANY member-tree node → its leaf stalls ----
@router.get("/node/{node_id}", response_model=NodeBrowseOut)
def resolve_node(node_id: str, db: Session = Depends(get_db)):
    """The orderable leaf stalls in a node's scope — a chain shows its whole group's stalls, a
    storefront shows itself. Powers the 'QR Menu' for a Chain row (a group/brand browse)."""
    node = org_tree.node_for(db, node_id)
    if node is None:
        raise NotFoundError("Location not found", code="node_not_found")
    menus = catalog_service.direct_storefronts(db, node)   # direct children only (not nested SF)
    order_paths = _stall_order_paths(db, menus)
    stalls = [
        StallRef(menu_id=m.id, stall_name=m.stall_name or m.name, cuisine=m.cuisine, logo=m.logo,
                 is_open=m.is_open, item_count=catalog_service.menu_item_count(db, m.id),
                 order_path=order_paths.get(m.id))
        for m in menus
    ]
    return NodeBrowseOut(node_id=node.id, name=node.name or node.id,
                         is_group=not node.sells, stalls=stalls)


def _stall_order_paths(db: Session, menus) -> dict[str, str]:
    """Per-stall full-ordering link `/t/{token}`, set ONLY for a dedicated storefront venue — its
    outlet hosts exactly one (active) menu and has its own table QR. A stall in a shared foodcourt
    outlet (many menus on one outlet/token) is left out, so the group browse keeps its in-place
    sheet for those instead of navigating the whole venue away."""
    from app.models.catalog import Menu
    from app.models.tenancy import QRCode

    outlet_ids = {m.outlet_id for m in menus}
    if not outlet_ids:
        return {}
    menus_per_outlet: dict[str, int] = {}
    for oid in db.scalars(select(Menu.outlet_id).where(Menu.outlet_id.in_(outlet_ids), Menu.is_active.is_(True))).all():
        menus_per_outlet[oid] = menus_per_outlet.get(oid, 0) + 1
    outlet_token: dict[str, str] = {}
    for oid, token in db.execute(
        select(QRCode.outlet_id, QRCode.token).where(QRCode.outlet_id.in_(outlet_ids)).order_by(QRCode.token)
    ).all():
        outlet_token.setdefault(oid, token)
    paths: dict[str, str] = {}
    for m in menus:
        token = outlet_token.get(m.outlet_id)
        if token and menus_per_outlet.get(m.outlet_id, 0) == 1:   # dedicated storefront venue
            paths[m.id] = f"/t/{token}"
    return paths


@router.get("/node/{node_id}/menu/{menu_id}", response_model=MenuOut)
def resolve_node_menu(node_id: str, menu_id: str, db: Session = Depends(get_db),
                      lang: str | None = Query(default=None),
                      accept_language: str | None = Header(default=None)):
    """Full menu for a stall reachable in the node's scope — validated so a node link can only
    reach stalls actually within that node (its leaves or stalls leased into it)."""
    node = org_tree.node_for(db, node_id)
    if node is None:
        raise NotFoundError("Location not found", code="node_not_found")
    if menu_id not in {m.id for m in catalog_service.node_scope_stalls(db, node)}:
        raise NotFoundError("Stall menu not found", code="menu_not_found")
    locale = i18n.resolve_locale(override=lang, accept_language=accept_language)
    return MenuOut.model_validate(i18n.localize_menu(catalog_service.get_menu_full(db, menu_id), locale))


@router.get("/{token}/menu/{menu_id}", response_model=MenuOut)
def resolve_stall_menu(token: str, menu_id: str, db: Session = Depends(get_db),
                       lang: str | None = Query(default=None),
                       accept_language: str | None = Header(default=None)):
    """Full menu for one stall reachable at the token's venue — the venue's own stalls OR stalls
    leased in from another owner. A menu that is neither at the venue nor leased in is rejected,
    so a QR code can never reach an arbitrary outlet's menu."""
    qr = qr_service.resolve_token(db, token)
    menu = catalog_service.get_venue_stall_menu(db, qr.outlet_id, menu_id)
    merchant = db.get(Merchant, qr.merchant_id)
    locale = i18n.resolve_locale(override=lang, tenant_default=_tenant_default_locale(merchant),
                                 accept_language=accept_language)
    return MenuOut.model_validate(i18n.localize_menu(menu, locale))
