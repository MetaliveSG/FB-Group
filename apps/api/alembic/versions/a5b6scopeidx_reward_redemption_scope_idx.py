"""reward_redemptions.scope_node_id index (model has index=True; migration was missing)

The voucher scope column `RewardRedemption.scope_node_id` is declared `index=True` in the model,
but no migration created the index — SQLite `create_all` builds it silently, real Postgres did not,
so CI's drift guard flagged it. This adds the missing index.

Revision ID: a5b6scopeidx
Revises: z4a5pinenc
Create Date: 2026-06-07
"""
from alembic import op

revision = "a5b6scopeidx"
down_revision = "z4a5pinenc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_reward_redemptions_scope_node_id"),
        "reward_redemptions",
        ["scope_node_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reward_redemptions_scope_node_id"), table_name="reward_redemptions")
