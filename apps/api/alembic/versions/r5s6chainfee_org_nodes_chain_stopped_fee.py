"""org_nodes: chain_stopped + subscription_fee (Chain/Storefront model)

Revision ID: r5s6chainfee
Revises: q4r5orgnodename
Create Date: 2026-06-01

Member-tree standardised to Chain (structural) + Storefront (sells). Two new per-node columns:
`chain_stopped` (a Chain whose children may only be Storefronts) and `subscription_fee` (per-node
SaaS price, independent of parent; NULL = inherit). chain_stopped is NOT NULL with a server_default
of false so existing rows backfill; subscription_fee is nullable. The server_default is dropped
after backfill so the column matches the model (Python-side default only — no drift).
"""
from alembic import op
import sqlalchemy as sa

revision = "r5s6chainfee"
down_revision = "q4r5orgnodename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "org_nodes",
        sa.Column("chain_stopped", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("org_nodes", "chain_stopped", server_default=None)
    op.add_column("org_nodes", sa.Column("subscription_fee", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("org_nodes", "subscription_fee")
    op.drop_column("org_nodes", "chain_stopped")
