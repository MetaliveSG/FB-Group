"""customer_consents: PDPA consent audit at capture (+ marketing opt-in default)

Revision ID: t7u8consent
Revises: s6t7venuelease
Create Date: 2026-06-05

Append-only consent trail (one row per grant/withdraw), keyed to the data-controller merchant + the
purpose ("terms"|"marketing"). Marketing consent is now EXPRESS opt-in: `customers.marketing_consent`
flips to default false. Existing rows are reset to false (no express consent was ever recorded for them).
See app/models/identity.py::CustomerConsent + app/services/consent.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "t7u8consent"
down_revision = "s6t7venuelease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_consents",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.String(length=32), nullable=False),
        sa.Column("merchant_id", sa.String(length=32), nullable=True),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_consents_customer_id", "customer_consents", ["customer_id"])
    op.create_index("ix_customer_consents_merchant_id", "customer_consents", ["merchant_id"])

    # Marketing is now express opt-in. Reset existing customers to false (none gave express consent) and
    # set the column default to false going forward.
    op.execute("UPDATE customers SET marketing_consent = false")
    op.alter_column("customers", "marketing_consent", server_default=sa.text("false"))


def downgrade() -> None:
    op.alter_column("customers", "marketing_consent", server_default=sa.text("true"))
    op.drop_index("ix_customer_consents_merchant_id", table_name="customer_consents")
    op.drop_index("ix_customer_consents_customer_id", table_name="customer_consents")
    op.drop_table("customer_consents")
