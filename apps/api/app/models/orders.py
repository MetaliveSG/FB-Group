"""Orders + order line items. Supports QR dine-in and cashier/manual channels."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import FulfilmentStatus, OrderChannel, OrderStatus, OrderType


class Order(PKMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[str] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"), index=True)
    table_id: Mapped[str | None] = mapped_column(ForeignKey("tables.id", ondelete="SET NULL"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    channel: Mapped[str] = mapped_column(String(12), default=OrderChannel.QR.value)
    order_type: Mapped[str] = mapped_column(String(12), default=OrderType.DINE_IN.value)
    status: Mapped[str] = mapped_column(String(12), default=OrderStatus.PENDING.value, index=True)
    # Kitchen/ticket state, SEPARATE from `status` (payment). The KDS owns it; READY = ready for pick-up.
    fulfilment_status: Mapped[str] = mapped_column(String(12), default=FulfilmentStatus.QUEUED.value, index=True)

    # External-system reference (an Order is the first instance of the document+lines pattern;
    # `source` = the originating system e.g. 'pos:qashier', `external_id` = its order id). Used by
    # the POS integration API (Phase 3) to reconcile + dedup pushed orders. Null for native QR.
    source: Mapped[str | None] = mapped_column(String(40), index=True)
    external_id: Mapped[str | None] = mapped_column(String(80), index=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    service_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    # Voucher discount applied at the till (cashier scans/enters a voucher). total = subtotal +
    # service_charge + tax − discount_amount, floored at 0. See app/services/vouchers.py.
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    voucher_code: Mapped[str | None] = mapped_column(String(32))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    placed_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(PKMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    menu_item_id: Mapped[str | None] = mapped_column(ForeignKey("menu_items.id", ondelete="SET NULL"))
    name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    modifiers: Mapped[list | None] = mapped_column(JSON, default=list)  # [{name, price_delta}]
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
