"""orders: external reference (source + external_id) for POS integration

Revision ID: l8i9j0orderref
Revises: k7h8i9ledger
Create Date: 2026-05-31

An Order is the first instance of the document+lines pattern; `source` (originating system,
e.g. 'pos:qashier') + `external_id` (its order id) let the POS integration API (Phase 3)
reconcile and dedup pushed orders. Both nullable — native QR/cashier orders leave them null.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "l8i9j0orderref"
down_revision: Union[str, None] = "k7h8i9ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("source", sa.String(length=40), nullable=True))
    op.add_column("orders", sa.Column("external_id", sa.String(length=80), nullable=True))
    op.create_index("ix_orders_source", "orders", ["source"])
    op.create_index("ix_orders_external_id", "orders", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_external_id", table_name="orders")
    op.drop_index("ix_orders_source", table_name="orders")
    op.drop_column("orders", "external_id")
    op.drop_column("orders", "source")
