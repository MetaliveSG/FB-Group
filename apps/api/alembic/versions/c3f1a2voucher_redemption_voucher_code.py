"""redemption voucher_code

Adds a dedicated voucher_code column to reward_redemptions (previously the code was
incorrectly stored in the short `status` column, which overflowed VARCHAR(16) on
PostgreSQL). Native ALTER on both Postgres and SQLite (nullable add).

Revision ID: c3f1a2voucher
Revises: 285e46b32559
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3f1a2voucher"
down_revision: Union[str, None] = "285e46b32559"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reward_redemptions", sa.Column("voucher_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("reward_redemptions", "voucher_code")
