"""org_nodes per-node module flags (3-state: rewards/qr_ordering/pos; NULL=inherit)

Adds the per-node module toggles (Phase A of the 3-module architecture). All NULL on add
= inherit → behaviour-neutral (resolve_modules falls back to Merchant.settings).

Revision ID: b6c7modflags
Revises: a5b6scopeidx
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = "b6c7modflags"
down_revision = "a5b6scopeidx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("org_nodes", sa.Column("mod_rewards", sa.Boolean(), nullable=True))
    op.add_column("org_nodes", sa.Column("mod_qr_ordering", sa.Boolean(), nullable=True))
    op.add_column("org_nodes", sa.Column("mod_pos", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("org_nodes", "mod_pos")
    op.drop_column("org_nodes", "mod_qr_ordering")
    op.drop_column("org_nodes", "mod_rewards")
