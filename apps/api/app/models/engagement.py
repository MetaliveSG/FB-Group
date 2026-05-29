"""Customer-facing engagement: redeemable reward catalog, spin-the-wheel segments,
and CRM follow-up tasks (Salesforce-style activities)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import (
    ActivityType,
    OpportunityStage,
    RewardKind,
    TaskPriority,
    TaskStatus,
    WheelPrizeKind,
)


class RewardCatalogItem(PKMixin, TimestampMixin, Base):
    """A reward a customer can redeem points for (merchant-scoped)."""

    __tablename__ = "reward_catalog_items"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(300), default="")
    cost_points: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default=RewardKind.VOUCHER.value)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class WheelSegment(PKMixin, TimestampMixin, Base):
    """One slice of a merchant's spin-the-wheel game."""

    __tablename__ = "wheel_segments"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    prize_kind: Mapped[str] = mapped_column(String(12), default=WheelPrizeKind.POINTS.value)
    prize_value: Mapped[int] = mapped_column(Integer, default=0)  # points awarded / voucher = 0
    voucher_name: Mapped[str | None] = mapped_column(String(120))
    weight: Mapped[int] = mapped_column(Integer, default=1)  # relative probability
    color: Mapped[str] = mapped_column(String(16), default="#cccccc")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class JackpotPrize(PKMixin, TimestampMixin, Base):
    """One reel symbol on a merchant's 3x3 jackpot game.

    All three reels share the same prize pool. Match 3 in the middle row
    (the payline) and the customer wins that item as a voucher.
    `weight` tunes how often the item shows up *and* how often it wins —
    rarer items mean bigger prizes hit less often. The "lose" outcome is
    synthesised by the service (no row in this table represents a loss).
    """

    __tablename__ = "jackpot_prizes"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    item_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    emoji: Mapped[str] = mapped_column(String(8), default="🍽️")
    weight: Mapped[int] = mapped_column(Integer, default=1)  # relative probability per reel
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class CrmTask(PKMixin, TimestampMixin, Base):
    """A follow-up task/activity on a customer (Salesforce-style)."""

    __tablename__ = "crm_tasks"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(8), default=TaskStatus.OPEN.value, index=True)
    priority: Mapped[str] = mapped_column(String(8), default=TaskPriority.NORMAL.value)
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Opportunity(PKMixin, TimestampMixin, Base):
    """A sales/retention deal on a customer (Salesforce Opportunity)."""

    __tablename__ = "opportunities"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pipeline_type: Mapped[str] = mapped_column(String(12), default="sales", index=True)
    stage: Mapped[str] = mapped_column(String(16), default=OpportunityStage.PROSPECTING.value, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)


class CustomerActivity(PKMixin, TimestampMixin, Base):
    """A logged interaction (call/email/meeting/whatsapp/note) — Salesforce 'Log Activity'."""

    __tablename__ = "customer_activities"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[str] = mapped_column(String(12), default=ActivityType.NOTE.value)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), default="")
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime)
    logged_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
