"""users.pin_hash — POS staff quick-login PIN

Revision ID: w1x2staffpin
Revises: v0w1campaignid
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "w1x2staffpin"
down_revision = "v0w1campaignid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pin_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pin_hash")
