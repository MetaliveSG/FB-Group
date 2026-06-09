"""org_nodes — add mod_wallet (the 4th module toggle: Wallet)

Binary + parent-gated like the other 3, but opt-in (DEFAULT false → every existing node starts wallet
OFF) and additionally gated by Table QR at resolve time (boundaries.resolve_modules). No effective
backfill needed — wallet is a new capability, off until an operator turns it on.

Revision ID: f0g1modwallet
Revises: e9f0walletnn
Create Date: 2026-06-09
"""
import sqlalchemy as sa
from alembic import op

revision = "f0g1modwallet"
down_revision = "e9f0walletnn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("org_nodes", sa.Column("mod_wallet", sa.Boolean(), nullable=False,
                                         server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("org_nodes", "mod_wallet")
