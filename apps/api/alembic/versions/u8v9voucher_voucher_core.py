"""voucher core: value/rules/redeemed fields on reward_redemptions + order discount

Revision ID: u8v9voucher
Revises: t7u8consent
Create Date: 2026-06-05

Turns reward_redemptions into the shared Voucher (value + rules + redeemed-state) and lets an order
carry a voucher discount. Backfills merchant_id from the loyalty account and normalises legacy status
values (redeemed/active → issued; those rows were issued-but-never-consumed). See
docs/architecture-vouchers.md + app/services/vouchers.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "u8v9voucher"
down_revision = "t7u8consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # reward_redemptions → voucher
    op.add_column("reward_redemptions", sa.Column("merchant_id", sa.String(length=32), nullable=True))
    op.add_column("reward_redemptions", sa.Column("value", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("reward_redemptions", sa.Column("min_spend", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("reward_redemptions", sa.Column("valid_until", sa.DateTime(), nullable=True))
    op.add_column("reward_redemptions", sa.Column("campaign_id", sa.String(length=32), nullable=True))
    op.add_column("reward_redemptions", sa.Column("per_period", sa.String(length=8), nullable=True))
    op.add_column("reward_redemptions", sa.Column("redeemed_at", sa.DateTime(), nullable=True))
    op.add_column("reward_redemptions", sa.Column("redeemed_by_user_id", sa.String(length=32), nullable=True))
    # Scope (campaign reach): the member-tree node whose subtree this voucher is redeemable in.
    # NULL = tenant-wide (the merchant). See docs/architecture-vouchers.md §6.
    op.add_column("reward_redemptions", sa.Column("scope_node_id", sa.String(length=32), nullable=True))
    op.create_index("ix_reward_redemptions_status", "reward_redemptions", ["status"])
    op.create_index("ix_reward_redemptions_voucher_code", "reward_redemptions", ["voucher_code"])
    op.create_index("ix_reward_redemptions_merchant_id", "reward_redemptions", ["merchant_id"])
    op.create_index("ix_reward_redemptions_campaign_id", "reward_redemptions", ["campaign_id"])

    # Backfill merchant_id from the loyalty account; normalise legacy statuses to "issued" (unused).
    op.execute(
        "UPDATE reward_redemptions r SET merchant_id = la.scope_id "
        "FROM loyalty_accounts la WHERE r.account_id = la.id AND la.scope_type = 'merchant'"
    )
    op.execute("UPDATE reward_redemptions SET status = 'issued' WHERE status IN ('redeemed', 'active')")

    # campaigns → scope node (reach across the member tree)
    op.add_column("campaigns", sa.Column("scope_node_id", sa.String(length=32), nullable=True))

    # orders → voucher discount
    op.add_column("orders", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("voucher_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "voucher_code")
    op.drop_column("orders", "discount_amount")
    op.drop_column("campaigns", "scope_node_id")
    op.drop_index("ix_reward_redemptions_campaign_id", table_name="reward_redemptions")
    op.drop_index("ix_reward_redemptions_merchant_id", table_name="reward_redemptions")
    op.drop_index("ix_reward_redemptions_voucher_code", table_name="reward_redemptions")
    op.drop_index("ix_reward_redemptions_status", table_name="reward_redemptions")
    for col in ("scope_node_id", "redeemed_by_user_id", "redeemed_at", "per_period", "campaign_id",
                "valid_until", "min_spend", "value", "merchant_id"):
        op.drop_column("reward_redemptions", col)
