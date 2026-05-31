"""Ordering, pricing, order-status lifecycle, and simulated checkout."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError
from app.core.money import money
from app.db.base import utcnow
from app.loyalty.engine import accrue_on_transaction
from app.models.catalog import Menu, MenuCategory, MenuItem, MenuModifier
from app.models.enums import (
    ORDER_TRANSITIONS,
    OrderChannel,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentStatus,
)
from app.models.identity import Customer
from app.models.orders import Order, OrderItem
from app.models.payments import Payment, Transaction
from app.models.tenancy import Outlet
from app.services import boundaries


@dataclass
class OrderItemInput:
    menu_item_id: str
    quantity: int = 1
    modifier_ids: list[str] = field(default_factory=list)


def _load_outlet(db: Session, outlet_id: str) -> Outlet:
    outlet = db.get(Outlet, outlet_id)
    if not outlet or not outlet.is_active:
        raise NotFoundError("Outlet not found", code="outlet_not_found")
    return outlet


def _validate_item_belongs_to_outlet(db: Session, item: MenuItem, outlet_id: str) -> None:
    # Resolve the item's menu via its category and confirm it belongs to this outlet.
    category = db.get(MenuCategory, item.category_id)
    menu = db.get(Menu, category.menu_id) if category else None
    if not menu or menu.outlet_id != outlet_id:
        raise ConflictError("Item does not belong to this outlet", code="invalid_item_outlet")


def create_order(
    db: Session,
    *,
    outlet_id: str,
    items: list[OrderItemInput],
    customer_id: str | None = None,
    table_id: str | None = None,
    channel: OrderChannel = OrderChannel.QR,
    order_type: OrderType = OrderType.DINE_IN,
    created_by_user_id: str | None = None,
    source: str | None = None,
    external_id: str | None = None,
) -> Order:
    if not items:
        raise ConflictError("Order must contain at least one item", code="empty_order")

    outlet = _load_outlet(db, outlet_id)
    # QR ordering is gated by the merchant's `qr_ordering_enabled` module flag (Phase 2):
    # a rewards-only merchant accepts no customer QR orders. Staff/POS channels are unaffected.
    if channel == OrderChannel.QR and not boundaries.module_flags(db, merchant_id=outlet.merchant_id)["qr_ordering_enabled"]:
        raise ConflictError("Online ordering is not enabled here", code="ordering_disabled")
    order = Order(
        merchant_id=outlet.merchant_id,
        brand_id=outlet.brand_id,
        outlet_id=outlet.id,
        table_id=table_id,
        customer_id=customer_id,
        created_by_user_id=created_by_user_id,
        channel=channel.value,
        order_type=order_type.value,
        status=OrderStatus.PENDING.value,
        placed_at=utcnow(),
        source=source,
        external_id=external_id,
    )
    db.add(order)
    db.flush()

    subtotal = Decimal("0.00")
    for inp in items:
        if inp.quantity < 1:
            raise ConflictError("Quantity must be >= 1", code="bad_quantity")
        item = db.get(MenuItem, inp.menu_item_id)
        if not item:
            raise NotFoundError(f"Menu item {inp.menu_item_id} not found", code="item_not_found")
        if not item.is_available:
            raise ConflictError(f"Item '{item.name}' is unavailable", code="item_unavailable")
        _validate_item_belongs_to_outlet(db, item, outlet.id)

        unit = item.price
        mod_snapshot = []
        for mid in inp.modifier_ids:
            mod = db.get(MenuModifier, mid)
            if not mod or mod.item_id != item.id:
                raise ConflictError("Invalid modifier for item", code="invalid_modifier")
            unit += mod.price_delta
            mod_snapshot.append({"name": mod.name, "price_delta": float(mod.price_delta)})

        line_total = money(unit * inp.quantity)
        subtotal += line_total
        db.add(OrderItem(
            order_id=order.id, menu_item_id=item.id, name_snapshot=item.name,
            unit_price=money(item.price), quantity=inp.quantity,
            modifiers=mod_snapshot, line_total=line_total,
        ))

    subtotal = money(subtotal)
    service_charge = money(subtotal * Decimal(str(settings.SERVICE_CHARGE_RATE))) \
        if order_type == OrderType.DINE_IN else Decimal("0.00")
    tax = money((subtotal + service_charge) * Decimal(str(settings.GST_RATE)))
    order.subtotal = subtotal
    order.service_charge = service_charge
    order.tax = tax
    order.total = money(subtotal + service_charge + tax)
    db.flush()
    return order


def update_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    current = OrderStatus(order.status)
    if new_status not in ORDER_TRANSITIONS[current]:
        raise ConflictError(
            f"Cannot move order from {current.value} to {new_status.value}",
            code="invalid_transition",
        )
    order.status = new_status.value
    if new_status == OrderStatus.COMPLETED:
        order.completed_at = utcnow()
    db.flush()
    return order


@dataclass
class CheckoutResult:
    payment: Payment
    transaction: Transaction | None
    points_earned: int = 0


def checkout(
    db: Session,
    *,
    order: Order,
    method: PaymentMethod,
    force_outcome: str | None = None,  # "success" | "fail" | None(=success)
) -> CheckoutResult:
    existing = db.scalar(
        select(Transaction).where(Transaction.order_id == order.id)
    )
    if existing:
        raise ConflictError("Order already paid", code="already_paid")

    success = force_outcome != "fail"
    payment = Payment(
        order_id=order.id,
        method=method.value,
        amount=order.total,
        status=PaymentStatus.SUCCESS.value if success else PaymentStatus.FAILED.value,
        reference=f"MOCK-{secrets.token_hex(6).upper()}" if success else None,
        failure_reason=None if success else "Simulated payment failure",
    )
    db.add(payment)
    db.flush()

    if not success:
        return CheckoutResult(payment=payment, transaction=None, points_earned=0)

    # Settle to the resolved settlement account (= the merchant today; Phase 2 resolves the
    # venue's settlement_mode). Routed through the boundary seam so the call site never changes.
    txn = Transaction(
        merchant_id=boundaries.settlement_account_id(db, order=order),
        outlet_id=order.outlet_id,
        customer_id=order.customer_id,
        order_id=order.id,
        payment_id=payment.id,
        amount=order.total,
    )
    db.add(txn)
    db.flush()

    points = 0
    # Loyalty accrual is gated by the merchant's `rewards_enabled` module flag (Phase 2):
    # a merchant running ordering/POS without the loyalty programme earns no coins.
    rewards_on = boundaries.module_flags(db, merchant_id=order.merchant_id)["rewards_enabled"]
    if order.customer_id and rewards_on:
        customer = db.get(Customer, order.customer_id)
        if customer:
            points = accrue_on_transaction(
                db, customer=customer, merchant_id=order.merchant_id,
                amount=order.total, order_id=order.id,
            )
            txn.points_earned = points

    # Payment succeeded → mark the order paid/completed so it no longer shows as
    # "pending" in order history (the capture loop closes here).
    order.status = OrderStatus.COMPLETED.value
    order.completed_at = utcnow()
    db.flush()
    return CheckoutResult(payment=payment, transaction=txn, points_earned=points)
