"""Stored-value wallet — closed-loop, deposit-only, scoped to a loyalty domain (the enterprise ring).

One wallet per (customer, loyalty_domain) → "FS Wallet" / "Tasty Wallet". FSG-issued, CIP-rails.
Money NEVER crosses a loyalty domain (single-purpose → light reg); cross-enterprise value is coins only
(coalition). See docs/wallet-scope.md + docs/payments-build-spec.md.

`WalletLedger` is the append-only source of truth (the same posting pattern as the coin ledger,
`reward_transactions`): `WalletAccount.balance` is a cache that MUST equal SUM(ledger.amount). Never mutate
or delete a row; corrections are new compensating postings. `amount` is signed (+credit / -debit)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin


class WalletAccount(PKMixin, TimestampMixin, Base):
    __tablename__ = "wallet_accounts"
    __table_args__ = (
        # One wallet per customer per enterprise (loyalty domain).
        UniqueConstraint("customer_id", "loyalty_domain_id", name="uq_wallet_customer_domain"),
        # Deposit-only stored value can never go negative (backstop; debit guards are the first line).
        CheckConstraint("balance >= 0", name="ck_wallet_balance_nonneg"),
        Index("ix_wallet_domain", "loyalty_domain_id"),
    )

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    # The enterprise ring this wallet belongs to (same boundary as the coin ledger). Money is closed-loop here.
    loyalty_domain_id: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")

    # Cached balance — MUST equal SUM(WalletLedger.amount) for this account.
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    # Auto-reload (Starbucks-style "balance < threshold → reload increment" via a saved card, off-session).
    auto_reload_enabled: Mapped[bool] = mapped_column(default=False)
    auto_reload_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("5.00"))
    auto_reload_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("20.00"))
    # PSP card token for off-session auto-reload (NULL = no card on file → manual top-up only).
    saved_payment_token: Mapped[str | None] = mapped_column(String(120))

    ledger: Mapped[list["WalletLedger"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class WalletLedger(PKMixin, TimestampMixin, Base):
    """Append-only, **hash-chained** money posting — the non-repudiable source of truth.

    Each row is linked to its predecessor by `prev_hash`; `entry_hash` = SHA-256 over the row's canonical
    fields ‖ prev_hash (see `app.services.wallet._entry_hash`). Any edit/insert/delete breaks the chain →
    `wallet.verify_integrity` detects it. Postgres additionally blocks UPDATE/DELETE via a trigger
    (migration `c7d8wallet`) so the ledger is immutable at the DB layer. Never mutate; corrections are new
    compensating postings. `amount` is signed (+credit / -debit)."""

    __tablename__ = "wallet_ledger"
    __table_args__ = (
        # Replay-safe per account (PSP webhook / retry). NULLs exempt (many allowed) on PG + SQLite.
        UniqueConstraint("wallet_account_id", "idempotency_key", name="uq_wallet_idempotency"),
        # Monotonic per-account sequence — gaps/reorders are detectable; anchors the hash chain.
        UniqueConstraint("wallet_account_id", "seq", name="uq_wallet_seq"),
        UniqueConstraint("entry_hash", name="uq_wallet_entry_hash"),
        CheckConstraint("balance_after >= 0", name="ck_wallet_ledger_balance_nonneg"),
        CheckConstraint("amount <> 0", name="ck_wallet_amount_nonzero"),
        Index("ix_wallet_ledger_account", "wallet_account_id"),
    )

    wallet_account_id: Mapped[str] = mapped_column(
        ForeignKey("wallet_accounts.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # per-account 1,2,3…
    entry_type: Mapped[str] = mapped_column(String(12), nullable=False)  # WalletEntryType
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # +credit / -debit
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(80))  # PSP ref / order id
    idempotency_key: Mapped[str | None] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(160), default="")
    # Tamper-evident chain (non-repudiation).
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    account: Mapped["WalletAccount"] = relationship(back_populates="ledger")
