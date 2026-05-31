"""The org spine (member-tree-map) — one self-referential node per org entity.

A thin *structural* table: identity + parent + materialised path + capability flags. The typed
tables (Merchant/Brand/Outlet/Menu) stay as the rich *profiles* (an OrgNode's `id` equals its
profile row's id). Structure/scoping reads the spine; attributes read the profile.

  * `parent_id` is the source of truth for the tree; `path`/`depth` are derived caches —
    `path` is a dotted lineage of node ids (`<merchant>.<brand>.<outlet>.<stall>`) so a whole
    subtree is one indexed `path LIKE '<prefix>.%'` read instead of a recursive walk.
  * `sells` marks an orderable endpoint (a "stall"/storefront — a leaf in practice, but may
    sit at any depth). `role` is a human display label only; the engine keys off the flags.
  * `loyalty_domain_id` / `settlement_account_id` are the two resolved boundaries (§5 of
    docs/architecture-org-tree.md); today both equal the merchant.

See `docs/architecture-org-tree.md`. Kept in sync with the typed tables by
`app/services/org_tree.py::sync_org_tree` (idempotent, like the seed bolt-ons).
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PKMixin, TimestampMixin

PATH_SEP = "."


class OrgNode(PKMixin, TimestampMixin, Base):
    __tablename__ = "org_nodes"
    __table_args__ = (
        # Powers "all sellable nodes under X" — the hottest subtree read (app/POS scope).
        Index("ix_org_nodes_path", "path"),
        Index("ix_org_nodes_domain", "loyalty_domain_id"),
    )

    # id == the profile entity id (merchant/brand/outlet/menu) — reused, never re-encodes position.
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("org_nodes.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # display label
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    path: Mapped[str] = mapped_column(String(512), nullable=False)

    # capability flags — the engine keys off these, not `role`
    sells: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_settlement_boundary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_loyalty_domain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # resolved boundary pointers (nearest declaring ancestor; both = merchant today)
    loyalty_domain_id: Mapped[str] = mapped_column(String(32), nullable=False)
    settlement_account_id: Mapped[str] = mapped_column(String(32), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
