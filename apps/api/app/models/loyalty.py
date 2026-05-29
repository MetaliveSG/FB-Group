"""Loyalty & rewards: merchant-isolated accounts + coalition accounts, configurable
reward rules (no hardcoded logic), and an append-only points ledger."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, Numeric, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import LoyaltyTier, RewardRuleType, RewardScope, RewardTxnType

# Coalition membership (merchants participating in a shared rewards program)
coalition_members = Table(
    "coalition_members",
    Base.metadata,
    Column("coalition_id", ForeignKey("coalitions.id", ondelete="CASCADE"), primary_key=True),
    Column("merchant_id", ForeignKey("merchants.id", ondelete="CASCADE"), primary_key=True),
)


class Coalition(PKMixin, TimestampMixin, Base):
    __tablename__ = "coalitions"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoyaltyAccount(PKMixin, TimestampMixin, Base):
    """A customer's points balance within a scope (one merchant OR one coalition).

    This row is also the merchant<->customer link: a merchant's CRM customers are
    those holding a merchant-scoped account.
    """

    __tablename__ = "loyalty_accounts"
    __table_args__ = (
        UniqueConstraint("customer_id", "scope_type", "scope_id", name="uq_loyalty_scope"),
    )

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(String(12), default=RewardScope.MERCHANT.value)
    scope_id: Mapped[str] = mapped_column(String(32), index=True)  # merchant_id or coalition_id

    # CRM record owner (Salesforce-style) — set on merchant-scoped accounts.
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(12), default=LoyaltyTier.BRONZE.value)

    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    total_spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    first_visit_at: Mapped[datetime | None] = mapped_column()
    last_visit_at: Mapped[datetime | None] = mapped_column()

    transactions: Mapped[list["RewardTransaction"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class RewardRule(PKMixin, TimestampMixin, Base):
    """Configurable reward rule. `config` holds the parameters so logic isn't hardcoded."""

    __tablename__ = "reward_rules"

    scope_type: Mapped[str] = mapped_column(String(12), default=RewardScope.MERCHANT.value)
    scope_id: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)  # RewardRuleType
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime | None] = mapped_column()
    valid_to: Mapped[datetime | None] = mapped_column()


class RewardTransaction(PKMixin, TimestampMixin, Base):
    """Append-only points ledger entry (earn / redeem / adjust / expire)."""

    __tablename__ = "reward_transactions"

    account_id: Mapped[str] = mapped_column(ForeignKey("loyalty_accounts.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    txn_type: Mapped[str] = mapped_column(String(12), nullable=False)  # RewardTxnType
    points: Mapped[int] = mapped_column(Integer, nullable=False)  # +earn / -redeem
    reason: Mapped[str] = mapped_column(String(160), default="")
    rule_code: Mapped[str | None] = mapped_column(String(48))
    expires_at: Mapped[datetime | None] = mapped_column()

    account: Mapped["LoyaltyAccount"] = relationship(back_populates="transactions")


class RewardRedemption(PKMixin, TimestampMixin, Base):
    __tablename__ = "reward_redemptions"

    account_id: Mapped[str] = mapped_column(ForeignKey("loyalty_accounts.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    reward_name: Mapped[str] = mapped_column(String(160), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="redeemed")
    voucher_code: Mapped[str | None] = mapped_column(String(32))
