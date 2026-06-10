"""orders — add fulfilment_status (the kitchen/KDS ticket state, separate from payment status)

The KDS owns a kitchen lifecycle (queued→preparing→ready→collected) orthogonal to `status` (which
tracks payment: COMPLETED = paid, drives reports/void). READY = ready for pick-up. New column NOT NULL
DEFAULT 'queued' (existing orders → queued; the KDS only surfaces PAID, not-yet-collected ones).

Revision ID: g1h2fulfilment
Revises: f0g1modwallet
Create Date: 2026-06-10
"""
import sqlalchemy as sa
from alembic import op

revision = "g1h2fulfilment"
down_revision = "f0g1modwallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("fulfilment_status", sa.String(12), nullable=False,
                                      server_default="queued"))
    op.create_index("ix_orders_fulfilment_status", "orders", ["fulfilment_status"])


def downgrade() -> None:
    op.drop_index("ix_orders_fulfilment_status", table_name="orders")
    op.drop_column("orders", "fulfilment_status")
