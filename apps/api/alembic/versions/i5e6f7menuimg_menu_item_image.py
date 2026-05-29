"""add image_url column to menu_items (real food photos)

Revision ID: i5e6f7menuimg
Revises: h4d5e6gender
Create Date: 2026-05-29

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "i5e6f7menuimg"
down_revision: Union[str, None] = "h4d5e6gender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("image_url", sa.String(length=400), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_items", "image_url")
