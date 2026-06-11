"""org_nodes — add theme (per-brand customer-app theming, cascade-merged)

Partial theme {primary, accent, logo_url}; NULL = inherit. Resolved by merging down the path so an
enterprise sets a house style and a brand overrides per key. Drives CSS-variable overrides on the
customer app.

Revision ID: j4k5theme
Revises: i3j4kdsstation
Create Date: 2026-06-11
"""
import sqlalchemy as sa
from alembic import op

revision = "j4k5theme"
down_revision = "i3j4kdsstation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("org_nodes", sa.Column("theme", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("org_nodes", "theme")
