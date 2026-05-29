"""Promotions & retention campaigns + WhatsApp-mock message log + redemption tracking."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import CampaignType, MessageStatus


class Campaign(PKMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(32), nullable=False)  # CampaignType
    segment_key: Mapped[str | None] = mapped_column(String(48))  # target audience segment
    message_template: Mapped[str] = mapped_column(String(1000), default="")
    reward_points: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()

    messages: Mapped[list["CampaignMessage"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignAudience(PKMixin, Base):
    __tablename__ = "campaign_audiences"

    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)


class CampaignMessage(PKMixin, TimestampMixin, Base):
    __tablename__ = "campaign_messages"

    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")
    to_address: Mapped[str] = mapped_column(String(64), default="")
    body: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(12), default=MessageStatus.QUEUED.value)
    provider_ref: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    campaign: Mapped["Campaign"] = relationship(back_populates="messages")


class CampaignRedemption(PKMixin, TimestampMixin, Base):
    __tablename__ = "campaign_redemptions"

    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
