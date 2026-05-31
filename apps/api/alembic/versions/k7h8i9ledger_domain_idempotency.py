"""ledger: domain stamp + idempotency on reward_transactions (posting substrate)

Revision ID: k7h8i9ledger
Revises: j6f7g8stallmenu
Create Date: 2026-05-31

Adds `loyalty_domain_id` (the posting's loyalty domain — backfilled from the owning
account's scope) and `idempotency_key` (caller-supplied dedup for a single posting), plus
a composite index that powers the (account, order) accrual-replay guard.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "k7h8i9ledger"
down_revision: Union[str, None] = "j6f7g8stallmenu"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Add nullable first so existing rows don't violate NOT NULL.
    op.add_column("reward_transactions", sa.Column("loyalty_domain_id", sa.String(length=32), nullable=True))
    op.add_column("reward_transactions", sa.Column("idempotency_key", sa.String(length=80), nullable=True))

    # 2) Backfill the domain stamp from the owning loyalty account's scope.
    op.execute(
        """
        UPDATE reward_transactions AS t
        SET loyalty_domain_id = a.scope_id
        FROM loyalty_accounts AS a
        WHERE a.id = t.account_id
        """
    )
    # Safety net for any orphaned rows (account deleted): stamp a sentinel so NOT NULL holds.
    op.execute("UPDATE reward_transactions SET loyalty_domain_id = 'unknown' WHERE loyalty_domain_id IS NULL")

    # 3) Now enforce NOT NULL.
    op.alter_column("reward_transactions", "loyalty_domain_id", existing_type=sa.String(length=32), nullable=False)

    # 4) Indexes + idempotency uniqueness (multiple NULLs allowed on Postgres).
    op.create_index("ix_reward_transactions_loyalty_domain_id", "reward_transactions", ["loyalty_domain_id"])
    op.create_index("ix_reward_txn_acct_order_type", "reward_transactions", ["account_id", "order_id", "txn_type"])
    op.create_unique_constraint("uq_reward_txn_idempotency", "reward_transactions", ["idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_reward_txn_idempotency", "reward_transactions", type_="unique")
    op.drop_index("ix_reward_txn_acct_order_type", table_name="reward_transactions")
    op.drop_index("ix_reward_transactions_loyalty_domain_id", table_name="reward_transactions")
    op.drop_column("reward_transactions", "idempotency_key")
    op.drop_column("reward_transactions", "loyalty_domain_id")
