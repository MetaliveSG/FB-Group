"""Simulated payments + financial transaction ledger (PoC).

Payment   = a payment attempt with a method + simulated outcome.
Transaction = ledger entry created on a *successful* payment, linking
              customer / outlet / order. Rewards are triggered off this.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import PaymentMethod, PaymentStatus


class Payment(PKMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(12), default=PaymentMethod.PAYNOW.value)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(12), default=PaymentStatus.PENDING.value, index=True)
    reference: Mapped[str | None] = mapped_column(String(64))  # mock gateway ref
    failure_reason: Mapped[str | None] = mapped_column(String(160))

    transaction: Mapped["Transaction | None"] = relationship(
        back_populates="payment", uselist=False
    )


class Transaction(PKMixin, TimestampMixin, Base):
    __tablename__ = "transactions"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[str] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    points_earned: Mapped[int] = mapped_column(default=0)

    payment: Mapped["Payment"] = relationship(back_populates="transaction")
