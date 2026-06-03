"""Leasing — the foodcourt/coffeeshop runtime built on the `leases` edge.

Three primitives, all keyed off `Lease.rent_type`:
  * `storefronts_at_venue` — what a diner can order from at a physical floor: house stalls (the
    venue's ownership children, via the spine) ∪ leased-in stalls (via `leases`). The shared QR.
  * `active_lease_for` — the live tenancy of a stall (or None for a house stall).
  * `gto_turnover_grants` — the ONLY place a lease widens visibility: a `GTO` lease lets the
    landlord READ the leased stall's turnover (to bill the %). `FIXED` adds nothing → the
    coffeeshop guarantee (landlord is blind) falls out of the path-based RBAC for free.

GUARDRAIL: the venue/lease link must NEVER widen RBAC except through `gto_turnover_grants`.
`org_tree.grants_for_node`/`outlet_ids_under` stay strictly path-based.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.leases import RENT_GTO, RENT_TYPES, Lease
from app.models.org import PATH_SEP, OrgNode
from app.services import org_tree


def active_lease_for(db: Session, storefront_id: str) -> Lease | None:
    """The live tenancy of a stall, or None for a house stall (no lease row)."""
    return db.scalar(
        select(Lease).where(Lease.tenant_node_id == storefront_id, Lease.is_active.is_(True))
    )


def storefronts_at_venue(db: Session, venue: OrgNode, *, active_only: bool = True) -> list[OrgNode]:
    """Sellable stalls at a physical venue = house stalls (ownership subtree) ∪ leased-in stalls
    (active leases pointing here). De-duplicated; the resolution primitive behind the shared QR."""
    seen: dict[str, OrgNode] = {n.id: n for n in org_tree.sellable_under(db, venue, active_only=active_only)}
    leased_ids = db.scalars(
        select(Lease.tenant_node_id).where(Lease.venue_id == venue.id, Lease.is_active.is_(True))
    ).all()
    for tid in leased_ids:
        node = db.get(OrgNode, tid)
        if node is not None and node.sells and (not active_only or node.is_active):
            seen.setdefault(node.id, node)
    return sorted(seen.values(), key=lambda n: n.path)


def gto_turnover_grants(db: Session, node: OrgNode) -> list[tuple[str, str]]:
    """A landlord assigned at `node` may READ the turnover of every GTO-leased stall whose VENUE
    lies in `node`'s subtree (never manage — read-only). Returns (tenant_settlement_id,
    tenant_storefront_id). FIXED leases are excluded → the landlord stays blind to them.
    """
    venue_ids = select(OrgNode.id).where(org_tree._subtree_filter(node.path))
    leases = db.scalars(
        select(Lease).where(
            Lease.venue_id.in_(venue_ids),
            Lease.rent_type == RENT_GTO,
            Lease.is_active.is_(True),
        )
    ).all()
    grants: list[tuple[str, str]] = []
    for ls in leases:
        tnode = db.get(OrgNode, ls.tenant_node_id)
        if tnode is not None:
            grants.append((tnode.settlement_account_id, tnode.id))
    return grants


# ---- lease management (the venue operator grants/edits tenancies) ----------
def list_leases_for_venue(db: Session, venue: OrgNode) -> list[Lease]:
    return list(db.scalars(select(Lease).where(Lease.venue_id == venue.id).order_by(Lease.id)).all())


def _normalise_terms(rent_type: str | None, rate: Decimal | None) -> str:
    """Validate (rent_type, rate) and return the upper-cased rent_type. GTO rate is a percentage."""
    rt = (rent_type or "").upper()
    if rt not in RENT_TYPES:
        raise AppError("rent_type must be FIXED or GTO", code="bad_rent_type", status_code=400)
    if rate is None or rate < 0:
        raise AppError("rate must be >= 0", code="bad_rate", status_code=400)
    if rt == RENT_GTO and rate > 100:
        raise AppError("A GTO rate is a percentage (0–100)", code="bad_gto_rate", status_code=400)
    return rt


def create_lease(db: Session, *, venue: OrgNode, tenant_node_id: str, rent_type: str,
                 rate: Decimal) -> Lease:
    """Lease a stall into a venue. The venue is a Chain (foodcourt/coffeeshop floor); the tenant is
    a Storefront in a DIFFERENT ownership branch (a house stall — owned by the venue — needs no
    lease). Enforces ≤1 active lease per stall."""
    if venue.sells:
        raise AppError("A venue must be a Chain (a Storefront cannot host stalls)",
                       code="bad_venue", status_code=400)
    tenant = db.get(OrgNode, tenant_node_id)
    if tenant is None:
        raise NotFoundError("Tenant stall not found", code="tenant_not_found")
    if not tenant.sells:
        raise AppError("A tenant must be a Storefront (the sellable stall)",
                       code="bad_tenant", status_code=400)
    if tenant.id == venue.id:
        raise AppError("A venue cannot lease to itself", code="self_lease", status_code=400)
    if tenant.path == venue.path or tenant.path.startswith(venue.path + PATH_SEP):
        raise AppError("This stall is already owned by the venue (a house stall) — no lease needed",
                       code="house_stall", status_code=400)
    rt = _normalise_terms(rent_type, rate)
    if active_lease_for(db, tenant.id) is not None:
        raise AppError("This stall already has an active lease", code="already_leased",
                       status_code=409)
    lease = Lease(venue_id=venue.id, tenant_node_id=tenant.id, rent_type=rt, rate=rate, is_active=True)
    db.add(lease)
    db.flush()
    return lease


def get_venue_lease(db: Session, venue: OrgNode, lease_id: str) -> Lease:
    lease = db.get(Lease, lease_id)
    if lease is None or lease.venue_id != venue.id:
        raise NotFoundError("Lease not found", code="lease_not_found")
    return lease


def update_lease(db: Session, *, lease: Lease, rent_type: str | None = None,
                 rate: Decimal | None = None, is_active: bool | None = None) -> Lease:
    new_type = _normalise_terms(rent_type or lease.rent_type,
                                lease.rate if rate is None else rate)
    lease.rent_type = new_type
    if rate is not None:
        lease.rate = rate
    if is_active is not None:
        if is_active and not lease.is_active and active_lease_for(db, lease.tenant_node_id) is not None:
            raise AppError("This stall already has another active lease", code="already_leased",
                           status_code=409)
        lease.is_active = is_active
    db.flush()
    return lease


def delete_lease(db: Session, lease: Lease) -> None:
    db.delete(lease)
    db.flush()
