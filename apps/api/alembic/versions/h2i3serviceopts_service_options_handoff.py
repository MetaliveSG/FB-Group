"""service options (fulfilment) — orders.hand_off + org_nodes.service_options

Two-axis fulfilment (see docs/architecture-fulfilment-modes.md): the order records the hand-off axis
(self_pickup | served) alongside order_type (dining context); a storefront declares its enabled SET of
service options (cascade-resolved JSON list of keys). Back-compat: hand_off DEFAULT 'served' (existing
table-QR orders were table service); service_options NULL = inherit → default ['dine_in_served'].

Revision ID: h2i3serviceopts
Revises: g1h2fulfilment
Create Date: 2026-06-10
"""
import sqlalchemy as sa
from alembic import op

revision = "h2i3serviceopts"
down_revision = "g1h2fulfilment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("hand_off", sa.String(12), nullable=False, server_default="served"))
    op.add_column("org_nodes", sa.Column("service_options", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("org_nodes", "service_options")
    op.drop_column("orders", "hand_off")
