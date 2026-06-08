"""stored-value wallet — wallet_accounts + wallet_ledger (closed-loop, deposit-only, domain-scoped)

FS Wallet / Tasty Wallet: one wallet per (customer, loyalty_domain). Append-only ledger; balance = SUM.
See docs/wallet-scope.md + docs/payments-build-spec.md.

Revision ID: c7d8wallet
Revises: b6c7modflags
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "c7d8wallet"
down_revision = "b6c7modflags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_accounts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.String(length=32), nullable=False),
        sa.Column("loyalty_domain_id", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("auto_reload_enabled", sa.Boolean(), nullable=True),
        sa.Column("auto_reload_threshold", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("auto_reload_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("saved_payment_token", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "loyalty_domain_id", name="uq_wallet_customer_domain"),
        sa.CheckConstraint("balance >= 0", name="ck_wallet_balance_nonneg"),
    )
    op.create_index("ix_wallet_accounts_customer_id", "wallet_accounts", ["customer_id"])
    op.create_index("ix_wallet_domain", "wallet_accounts", ["loyalty_domain_id"])

    op.create_table(
        "wallet_ledger",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("wallet_account_id", sa.String(length=32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=12), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("source_ref", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.String(length=160), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["wallet_account_id"], ["wallet_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wallet_account_id", "idempotency_key", name="uq_wallet_idempotency"),
        sa.UniqueConstraint("wallet_account_id", "seq", name="uq_wallet_seq"),
        sa.UniqueConstraint("entry_hash", name="uq_wallet_entry_hash"),
        sa.CheckConstraint("balance_after >= 0", name="ck_wallet_ledger_balance_nonneg"),
        sa.CheckConstraint("amount <> 0", name="ck_wallet_amount_nonzero"),
    )
    op.create_index("ix_wallet_ledger_wallet_account_id", "wallet_ledger", ["wallet_account_id"])
    op.create_index("ix_wallet_ledger_account", "wallet_ledger", ["wallet_account_id"])

    # Non-repudiation, DB-layer: make the ledger append-only (block UPDATE/DELETE). Postgres only.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION wallet_ledger_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'wallet_ledger is append-only (no UPDATE/DELETE) — corrections are new postings';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_wallet_ledger_immutable
        BEFORE UPDATE OR DELETE ON wallet_ledger
        FOR EACH ROW EXECUTE FUNCTION wallet_ledger_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_wallet_ledger_immutable ON wallet_ledger;")
    op.execute("DROP FUNCTION IF EXISTS wallet_ledger_immutable();")
    op.drop_index("ix_wallet_ledger_account", table_name="wallet_ledger")
    op.drop_index("ix_wallet_ledger_wallet_account_id", table_name="wallet_ledger")
    op.drop_table("wallet_ledger")
    op.drop_index("ix_wallet_domain", table_name="wallet_accounts")
    op.drop_index("ix_wallet_accounts_customer_id", table_name="wallet_accounts")
    op.drop_table("wallet_accounts")
