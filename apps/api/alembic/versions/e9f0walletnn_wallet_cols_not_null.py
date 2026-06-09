"""wallet_accounts / wallet_ledger — set the model's NOT NULL columns NOT NULL

Drift fix. The wallet model declares these columns non-optional (Mapped[...] with a Python default),
but migration c7d8wallet created them nullable → CI's model-drift guard fails. They always get a value
from the ORM default on insert, so backfill any stray NULLs to the model default, then enforce NOT NULL.
No server_default (the model has none — keep DB and model in lockstep).

Revision ID: e9f0walletnn
Revises: d8e9modbinary
Create Date: 2026-06-09
"""
import sqlalchemy as sa
from alembic import op

revision = "e9f0walletnn"
down_revision = "d8e9modbinary"
branch_labels = None
depends_on = None

# column → (model default, SQLAlchemy type) for the backfill + NOT NULL
_ACCOUNTS = [
    ("currency", "'SGD'", sa.String(3)),
    ("balance", "0.00", sa.Numeric(12, 2)),
    ("auto_reload_enabled", "false", sa.Boolean()),
    ("auto_reload_threshold", "5.00", sa.Numeric(12, 2)),
    ("auto_reload_amount", "20.00", sa.Numeric(12, 2)),
]
_LEDGER = [("reason", "''", sa.String(160))]


def upgrade() -> None:
    for table, cols in (("wallet_accounts", _ACCOUNTS), ("wallet_ledger", _LEDGER)):
        for col, default_sql, coltype in cols:
            op.execute(f"UPDATE {table} SET {col} = {default_sql} WHERE {col} IS NULL")
            op.alter_column(table, col, existing_type=coltype, nullable=False)


def downgrade() -> None:
    for table, cols in (("wallet_accounts", _ACCOUNTS), ("wallet_ledger", _LEDGER)):
        for col, _default_sql, coltype in cols:
            op.alter_column(table, col, existing_type=coltype, nullable=True)
