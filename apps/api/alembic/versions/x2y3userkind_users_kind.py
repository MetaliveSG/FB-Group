"""users.kind — segregate web vs POS accounts

Revision ID: x2y3userkind
Revises: w1x2staffpin
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = "x2y3userkind"
down_revision = "w1x2staffpin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default 'web' backfills every existing row; matches the model's Python default (NOT NULL).
    op.add_column(
        "users",
        sa.Column("kind", sa.String(length=8), nullable=False, server_default="web"),
    )


def downgrade() -> None:
    op.drop_column("users", "kind")
