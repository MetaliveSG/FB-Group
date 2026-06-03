"""Leases — the venue↔stall tenancy edge (foodcourt vs coffeeshop).

A `Lease` is an **associative entity** between two `org_nodes`: the **venue** (a Chain that owns
the shared tables/QR — a foodcourt or coffeeshop floor) and the **tenant stall** (a Storefront).
Its two FKs ARE the location link, and the row carries the *terms* of the tenancy. `rent_type` lives
here — on the relationship — not on either node, because it's a property of the pairing, not of the
stall (a stall could be GTO in one mall and fixed in another).

The whole foodcourt/coffeeshop feature is THIS one table: NO columns are added to `org_nodes` (the
spine stays clean). A leased stall's floor comes from its lease row; a HOUSE stall's floor comes
from the existing `parent_id`/`path` (it's an ownership child of the venue → no lease row at all).

`rent_type` gates exactly two code paths and nowhere else (see `app/services/leasing.py`):
  * **visibility** — `GTO` grants the landlord a read-only *turnover* view of the leased stall (to
    bill the %); `FIXED` grants nothing (the coffeeshop guarantee — landlord is blind).
  * **settlement** — `GTO` routes `rate`% up to the landlord per sale; `FIXED` routes nothing (flat
    rent, billed monthly off `rate`). The per-sale split is a later phase; the read-grant ships now.

See `docs/architecture-org-tree.md` §10.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PKMixin, TimestampMixin

RENT_FIXED = "FIXED"   # coffeeshop / kopitiam — flat $/month, landlord sees NOTHING
RENT_GTO = "GTO"       # foodcourt — % of turnover, landlord gets a read-only turnover view
RENT_TYPES = (RENT_FIXED, RENT_GTO)


class Lease(PKMixin, TimestampMixin, Base):
    __tablename__ = "leases"
    __table_args__ = (
        # One lease per (venue, stall) pair; ≤1 *active* lease per stall is enforced in code.
        UniqueConstraint("venue_id", "tenant_node_id", name="uq_lease_venue_tenant"),
        Index("ix_leases_venue", "venue_id"),
        Index("ix_leases_tenant", "tenant_node_id"),
        CheckConstraint("rent_type IN ('FIXED','GTO')", name="ck_lease_rent_type"),
        # GTO rate is a percentage; FIXED rate is a dollar amount (no upper bound).
        CheckConstraint("rent_type <> 'GTO' OR (rate >= 0 AND rate <= 100)", name="ck_lease_gto_pct"),
    )

    venue_id: Mapped[str] = mapped_column(
        ForeignKey("org_nodes.id", ondelete="CASCADE"), nullable=False)        # landlord (a Chain)
    tenant_node_id: Mapped[str] = mapped_column(
        ForeignKey("org_nodes.id", ondelete="CASCADE"), nullable=False)        # the stall (a Storefront)
    rent_type: Mapped[str] = mapped_column(String(8), nullable=False)          # FIXED | GTO
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)      # FIXED $/mo · GTO percent
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    deposit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
