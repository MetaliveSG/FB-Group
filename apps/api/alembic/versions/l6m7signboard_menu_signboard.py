"""menus — add signboard_url (per-stall branded signboard image for the directory card)

The stall directory card shows the stall's real retro signboard graphic; the emoji `logo` is the
fallback. Null = use the emoji. Additive, nullable — no backfill needed.

Revision ID: l6m7signboard
Revises: k5l6i18n
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op

revision = "l6m7signboard"
down_revision = "k5l6i18n"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menus", sa.Column("signboard_url", sa.String(length=400), nullable=True))


def downgrade() -> None:
    op.drop_column("menus", "signboard_url")
