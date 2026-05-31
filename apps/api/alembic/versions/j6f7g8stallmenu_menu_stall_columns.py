"""add stall columns to menus (foodcourt: a Menu is a stall)

Revision ID: j6f7g8stallmenu
Revises: i5e6f7menuimg
Create Date: 2026-05-30

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "j6f7g8stallmenu"
down_revision: Union[str, None] = "i5e6f7menuimg"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menus", sa.Column("stall_name", sa.String(length=120), nullable=True))
    op.add_column("menus", sa.Column("cuisine", sa.String(length=80), nullable=True))
    op.add_column("menus", sa.Column("logo", sa.String(length=16), nullable=True))
    op.add_column("menus", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("menus", sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("menus", "is_open")
    op.drop_column("menus", "sort_order")
    op.drop_column("menus", "logo")
    op.drop_column("menus", "cuisine")
    op.drop_column("menus", "stall_name")
