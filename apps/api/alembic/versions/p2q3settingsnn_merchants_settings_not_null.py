"""merchants.settings NOT NULL — align schema with the model

Revision ID: p2q3settingsnn
Revises: n0k1l2idemscope
Create Date: 2026-06-01

`Merchant.settings` is non-nullable in the model (Mapped[dict], default=dict), but the column
was originally created nullable — so a fresh `alembic upgrade head` drifted from the models
(caught by the CI drift guard, invisible to pytest's SQLite create_all path). Backfill any
existing NULLs to an empty object, then enforce NOT NULL. No server_default: the model uses a
Python-side default only, so adding one here would itself create drift.
"""
from alembic import op
import sqlalchemy as sa

revision = "p2q3settingsnn"
down_revision = "n0k1l2idemscope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE merchants SET settings = '{}' WHERE settings IS NULL")
    op.alter_column("merchants", "settings", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.alter_column("merchants", "settings", existing_type=sa.JSON(), nullable=True)
