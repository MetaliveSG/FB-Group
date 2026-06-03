"""org_nodes.name — human display label on the spine

Revision ID: q4r5orgnodename
Revises: p2q3settingsnn
Create Date: 2026-06-01

The org spine stored only `role` + flags; the human name lived in the typed profile
(Merchant/Brand/Outlet/Menu). The Org-Tree UI renders the spine directly and pure-spine nodes
(an Enterprise above the typed tables) have no profile row — so mirror a display `name` onto the
node. Nullable (model is `Mapped[str | None]`): additive, no backfill, no drift.
"""
from alembic import op
import sqlalchemy as sa

revision = "q4r5orgnodename"
down_revision = "p2q3settingsnn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("org_nodes", sa.Column("name", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("org_nodes", "name")
