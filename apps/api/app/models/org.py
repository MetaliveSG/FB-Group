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

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy import false
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
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # display label: CHAIN | STOREFRONT
    # Stop-chain: a Chain node whose children may ONLY be Storefronts (no more sub-Chains) — lets
    # a parent cap the structure. Meaningless on a Storefront (it has no children). See §1 model.
    chain_stopped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Per-node SaaS subscription fee — set independently, may be MORE or LESS than the parent
    # (explicit override; NULL = inherit the parent's). The billing engine (rollup/invoicing) is
    # a later phase; this just carries the figure. Money = Numeric(12,2) as Decimal.
    subscription_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # Human display name. The typed profile (Merchant/Brand/Outlet/Menu) is the source of truth
    # for synced nodes; mirrored here so the spine renders standalone (and so pure-spine nodes —
    # e.g. an Enterprise above the typed tables — carry a name with no profile row). Nullable so
    # the additive migration needs no backfill.
    name: Mapped[str | None] = mapped_column(String(120))
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    path: Mapped[str] = mapped_column(String(512), nullable=False)

    # capability flags — the engine keys off these, not `role`
    sells: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_settlement_boundary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_loyalty_domain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # module adoption — per-node toggles for the 3 modules, BINARY + parent-gated:
    # each node carries its OWN on/off; the effective value is AND-ed down the path
    # (a node is ON only if it AND every ancestor are ON). Default False (a fresh row is OFF;
    # node-creation / seed turn them on for a usable merchant). Resolved by boundaries.resolve_modules.
    mod_rewards: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)        # Intelligence
    mod_qr_ordering: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)    # Table QR
    mod_pos: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)            # POS
    # Wallet (stored-value) — opt-in (default OFF) and gated by Table QR (money to spend on orders →
    # no ordering channel ⇒ no wallet). Effective wallet = (AND of mod_wallet up the path) AND qr_ordering.
    mod_wallet: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)         # Wallet

    # Service options (fulfilment) — the SET of (dining-context × hand-off) options this storefront offers,
    # as a JSON list of SERVICE_OPTIONS keys. NULL = inherit (nearest declaring ancestor wins → default
    # restaurant table-service). A foodcourt sets ["dine_in_pickup","takeaway"] once high; stalls inherit.
    service_options: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # resolved boundary pointers (nearest declaring ancestor; both = merchant today)
    loyalty_domain_id: Mapped[str] = mapped_column(String(32), nullable=False)
    settlement_account_id: Mapped[str] = mapped_column(String(32), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
