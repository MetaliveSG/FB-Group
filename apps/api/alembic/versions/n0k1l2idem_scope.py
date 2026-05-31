"""ledger: scope idempotency_key uniqueness to the loyalty domain (tenant-safe)

Revision ID: n0k1l2idemscope
Revises: m9j0k1orgnode
Create Date: 2026-05-31

Security hardening (Phase 1 audit): a globally-unique idempotency_key would let one tenant's
key collide with another's (a cross-tenant DoS once the POS push API supplies keys). Scope the
uniqueness to (loyalty_domain_id, idempotency_key) — the correct idempotency boundary.
"""
from typing import Union

from alembic import op

revision: str = "n0k1l2idemscope"
down_revision: Union[str, None] = "m9j0k1orgnode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_reward_txn_idempotency", "reward_transactions", type_="unique")
    op.create_unique_constraint(
        "uq_reward_txn_idempotency", "reward_transactions", ["loyalty_domain_id", "idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_reward_txn_idempotency", "reward_transactions", type_="unique")
    op.create_unique_constraint("uq_reward_txn_idempotency", "reward_transactions", ["idempotency_key"])
