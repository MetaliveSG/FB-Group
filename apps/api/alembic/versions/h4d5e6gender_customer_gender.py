"""add gender column to customers (optional profile field)

Revision ID: h4d5e6gender
Revises: g3c4d5jackpot
Create Date: 2026-05-29

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "h4d5e6gender"
down_revision: Union[str, None] = "g3c4d5jackpot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("gender", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "gender")
