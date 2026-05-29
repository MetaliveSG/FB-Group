"""jackpot_prizes table — 3x3 jackpot game (match-3 in middle row → voucher)

Revision ID: g3c4d5jackpot
Revises: f1a2b3pipemode
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g3c4d5jackpot"
down_revision: Union[str, None] = "f1a2b3pipemode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jackpot_prizes",
        sa.Column("merchant_id", sa.String(length=32), nullable=False),
        sa.Column("item_name", sa.String(length=120), nullable=False),
        sa.Column("item_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("emoji", sa.String(length=8), nullable=False, server_default="🍽️"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jackpot_prizes_merchant_id", "jackpot_prizes", ["merchant_id"])


def downgrade() -> None:
    op.drop_index("ix_jackpot_prizes_merchant_id", table_name="jackpot_prizes")
    op.drop_table("jackpot_prizes")
