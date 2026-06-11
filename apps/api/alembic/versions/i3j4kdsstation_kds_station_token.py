"""kds_stations — per-outlet private station token (KDS auth hardening)

A revocable bearer token per outlet so a kitchen tablet runs /kds without a login (station binding,
not a person). Separate from the public QR token.

Revision ID: i3j4kdsstation
Revises: h2i3serviceopts
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op

revision = "i3j4kdsstation"
down_revision = "h2i3serviceopts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kds_stations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("merchant_id", sa.String(length=32), nullable=False),
        sa.Column("outlet_id", sa.String(length=32), nullable=False),
        sa.Column("token", sa.String(length=48), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kds_stations_merchant_id", "kds_stations", ["merchant_id"])
    op.create_index("ix_kds_stations_outlet_id", "kds_stations", ["outlet_id"])
    op.create_index("ix_kds_stations_token", "kds_stations", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_kds_stations_token", table_name="kds_stations")
    op.drop_index("ix_kds_stations_outlet_id", table_name="kds_stations")
    op.drop_index("ix_kds_stations_merchant_id", table_name="kds_stations")
    op.drop_table("kds_stations")
