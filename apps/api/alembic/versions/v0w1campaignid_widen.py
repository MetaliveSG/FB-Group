"""widen reward_redemptions.campaign_id to 64 (holds synthetic "welcome:{merchant_id}" ids)

Revision ID: v0w1campaignid
Revises: u8v9voucher
Create Date: 2026-06-05

The welcome-pack campaign id is "welcome:{merchant_id}" (40 chars) — overflowed VARCHAR(32) on
Postgres (SQLite tests don't enforce length). Widen to 64.
"""
from alembic import op
import sqlalchemy as sa

revision = "v0w1campaignid"
down_revision = "u8v9voucher"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("reward_redemptions", "campaign_id",
                    existing_type=sa.String(length=32), type_=sa.String(length=64), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("reward_redemptions", "campaign_id",
                    existing_type=sa.String(length=64), type_=sa.String(length=32), existing_nullable=True)
