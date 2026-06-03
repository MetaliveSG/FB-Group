"""Provision the typed ordering backing for a sellable member-tree node.

A Storefront created through the Platform Console (`POST /org/nodes`, or a `member_kind=storefront`
tenant via onboarding) is a spine node only — it has no menu, outlet or QR, so it can't be scanned
or take orders, and no "QR Menu" button appears for it. This module closes that seam: it gives a
sellable node its typed backing so it is immediately scannable + orderable, and the merchant console
shows a real outlet under the tenant's brand.

The one invariant the whole QR/menu resolver stack keys off is **menu.id == node.id** (see
`org_tree.sync_org_tree` and `catalog.node_scope_stalls`): a sellable spine node yields a stall only
when a Menu row carries the node's id. So we mint the Menu with `id=node.id`; the Outlet keeps its
own id (it is the location/venue, a separate row that anchors Order.outlet_id + the QR token).

NOTE (deliberate): we do NOT call `sync_org_tree` after provisioning. Sync would mirror the new typed
Outlet into a *second* (Chain) spine node and re-parent the Storefront beneath it — reshaping the
clean operator-built tree into the full typed depth. That convergence is the one-tree-collapse work
(see memory `collapse-one-tree-plan`); until then, leave UI-built trees as-is.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Menu
from app.models.org import OrgNode
from app.models.tenancy import Brand, DiningTable, Outlet, QRCode

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    return _SLUG_RE.sub("-", (name or "").lower()).strip("-") or "store"


def _token_for(node: OrgNode) -> str:
    """Stable, human-ish, unique QR token: slug of the name + a slice of the node id.
    The id slice guarantees uniqueness across same-named storefronts; <=48 chars (QRCode.token)."""
    return f"{_slug(node.name)[:30]}-{node.id[:8]}"


def _brand_for(db: Session, merchant_id: str) -> Brand:
    """The tenant's brand to hang the outlet under — the default brand onboarding created, or a
    freshly-minted one if somehow absent (keeps provisioning total even on hand-built data)."""
    brand = db.scalar(
        select(Brand).where(Brand.merchant_id == merchant_id).order_by(Brand.created_at, Brand.id)
    )
    if brand is None:
        brand = Brand(merchant_id=merchant_id, name="Default")
        db.add(brand)
        db.flush()
    return brand


def provision_storefront(db: Session, node: OrgNode) -> Outlet | None:
    """Give a sellable node (`node.sells`) its typed Outlet + Menu(id==node.id) + table + QR token.
    Idempotent: a no-op if the node isn't sellable or its Menu already exists. The Menu is created
    empty — the owner fills items via the merchant menu admin. Returns the Outlet (or None)."""
    if not node.sells:
        return None
    if db.get(Menu, node.id) is not None:   # already provisioned (menu.id == node.id)
        return None

    merchant_id = node.settlement_account_id
    brand = _brand_for(db, merchant_id)

    outlet = Outlet(merchant_id=merchant_id, brand_id=brand.id, name=node.name or "Storefront")
    db.add(outlet)
    db.flush()

    # menu.id == node.id is the resolver contract — do not let the PK default override it.
    menu = Menu(id=node.id, merchant_id=merchant_id, outlet_id=outlet.id,
                name=node.name or "Main Menu", stall_name=node.name)
    db.add(menu)

    table = DiningTable(merchant_id=merchant_id, outlet_id=outlet.id, label="T01")
    db.add(table)
    db.flush()

    db.add(QRCode(merchant_id=merchant_id, outlet_id=outlet.id, table_id=table.id,
                  token=_token_for(node)))
    db.flush()
    return outlet


def provision_missing(db: Session) -> dict:
    """Backfill: provision every sellable node that has no Menu yet (id==node.id). Idempotent —
    safe to re-run. Returns counts. Used to wire up storefronts created before this seam existed."""
    provisioned = 0
    have_menu = set(db.scalars(select(Menu.id)).all())
    for node in db.scalars(select(OrgNode).where(OrgNode.sells.is_(True))).all():
        if node.id not in have_menu:
            provision_storefront(db, node)
            provisioned += 1
    db.flush()
    return {"provisioned": provisioned}
