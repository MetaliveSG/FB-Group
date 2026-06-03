"""leases: venue↔stall tenancy edge (foodcourt GTO vs coffeeshop FIXED)

Revision ID: s6t7venuelease
Revises: r5s6chainfee
Create Date: 2026-06-02

The whole foodcourt/coffeeshop feature is ONE associative table; NO columns are added to org_nodes.
A lease's two FKs (venue, tenant stall) are the location link; `rent_type` carries the terms.
See docs/architecture-org-tree.md §10 + app/models/leases.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "s6t7venuelease"
down_revision = "r5s6chainfee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leases",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("venue_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_node_id", sa.String(length=32), nullable=False),
        sa.Column("rent_type", sa.String(length=8), nullable=False),
        sa.Column("rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("deposit", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["org_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_node_id"], ["org_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "tenant_node_id", name="uq_lease_venue_tenant"),
        sa.CheckConstraint("rent_type IN ('FIXED','GTO')", name="ck_lease_rent_type"),
        sa.CheckConstraint("rent_type <> 'GTO' OR (rate >= 0 AND rate <= 100)", name="ck_lease_gto_pct"),
    )
    op.create_index("ix_leases_venue", "leases", ["venue_id"])
    op.create_index("ix_leases_tenant", "leases", ["tenant_node_id"])


def downgrade() -> None:
    op.drop_index("ix_leases_tenant", "leases")
    op.drop_index("ix_leases_venue", "leases")
    op.drop_table("leases")
