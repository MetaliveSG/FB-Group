"""pipeline_type on opportunities + settings on merchants

Adds configurable pipeline modes (sales/winback) and a per-merchant settings JSON
(feature toggles, e.g. pipeline_enabled). Native ALTER on Postgres + SQLite.

Revision ID: f1a2b3pipemode
Revises: e7f8a9oppact
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3pipemode"
down_revision: Union[str, None] = "e7f8a9oppact"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunities",
                  sa.Column("pipeline_type", sa.String(length=12), nullable=False, server_default="sales"))
    op.create_index("ix_opportunities_pipeline_type", "opportunities", ["pipeline_type"])
    op.add_column("merchants", sa.Column("settings", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("merchants", "settings")
    op.drop_index("ix_opportunities_pipeline_type", table_name="opportunities")
    op.drop_column("opportunities", "pipeline_type")
