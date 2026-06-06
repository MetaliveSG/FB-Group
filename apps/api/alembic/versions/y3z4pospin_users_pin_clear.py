"""users.pin — readable POS till PIN (owner-viewable)

Revision ID: y3z4pospin
Revises: x2y3userkind
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = "y3z4pospin"
down_revision = "x2y3userkind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pin", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pin")
