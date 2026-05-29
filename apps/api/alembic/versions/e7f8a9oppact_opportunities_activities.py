"""opportunities + customer_activities

Salesforce-style Opportunities (pipeline) and logged Activities.
Plain create_table (native on Postgres and SQLite).

Revision ID: e7f8a9oppact
Revises: c3f1a2voucher
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9oppact"
down_revision: Union[str, None] = "c3f1a2voucher"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("merchant_id", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("owner_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_merchant_id", "opportunities", ["merchant_id"])
    op.create_index("ix_opportunities_customer_id", "opportunities", ["customer_id"])
    op.create_index("ix_opportunities_stage", "opportunities", ["stage"])
    op.create_index("ix_opportunities_owner_user_id", "opportunities", ["owner_user_id"])

    op.create_table(
        "customer_activities",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("merchant_id", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.String(length=32), nullable=False),
        sa.Column("activity_type", sa.String(length=12), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("logged_by_user_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["logged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_activities_merchant_id", "customer_activities", ["merchant_id"])
    op.create_index("ix_customer_activities_customer_id", "customer_activities", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_activities_customer_id", table_name="customer_activities")
    op.drop_index("ix_customer_activities_merchant_id", table_name="customer_activities")
    op.drop_table("customer_activities")
    op.drop_index("ix_opportunities_owner_user_id", table_name="opportunities")
    op.drop_index("ix_opportunities_stage", table_name="opportunities")
    op.drop_index("ix_opportunities_customer_id", table_name="opportunities")
    op.drop_index("ix_opportunities_merchant_id", table_name="opportunities")
    op.drop_table("opportunities")
