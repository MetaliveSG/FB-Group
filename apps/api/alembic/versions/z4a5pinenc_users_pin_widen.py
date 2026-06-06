"""users.pin → String(255) for encrypted-at-rest POS PINs (Fernet ciphertext)

Revision ID: z4a5pinenc
Revises: y3z4pospin
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "z4a5pinenc"
down_revision = "y3z4pospin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "pin", type_=sa.String(length=255), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("users", "pin", type_=sa.String(length=8), existing_nullable=True)
