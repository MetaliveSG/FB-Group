"""org spine: org_nodes (member-tree-map) — adjacency + materialised path

Revision ID: m9j0k1orgnode
Revises: l8i9j0orderref
Create Date: 2026-05-31

Thin structural table; one node per typed entity (Merchant/Brand/Outlet/Menu), kept in sync by
`app/services/org_tree.py::sync_org_tree`. Table only — rows are populated by the idempotent
sync (run via seed / `ensure_org_tree()`), matching the seed-bolt-on convention.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "m9j0k1orgnode"
down_revision: Union[str, None] = "l8i9j0orderref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_nodes",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("parent_id", sa.String(length=32), sa.ForeignKey("org_nodes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("sells", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_settlement_boundary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_loyalty_domain", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("loyalty_domain_id", sa.String(length=32), nullable=False),
        sa.Column("settlement_account_id", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_org_nodes_parent_id", "org_nodes", ["parent_id"])
    op.create_index("ix_org_nodes_path", "org_nodes", ["path"])
    op.create_index("ix_org_nodes_domain", "org_nodes", ["loyalty_domain_id"])


def downgrade() -> None:
    op.drop_index("ix_org_nodes_domain", table_name="org_nodes")
    op.drop_index("ix_org_nodes_path", table_name="org_nodes")
    op.drop_index("ix_org_nodes_parent_id", table_name="org_nodes")
    op.drop_table("org_nodes")
