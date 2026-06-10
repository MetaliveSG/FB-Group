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
    DEFAULT_SERVICE_OPTIONS,
    FULFILMENT_TRANSITIONS,
    ORDER_TRANSITIONS,
    SERVICE_OPTIONS,
    FulfilmentStatus,
    HandOff,
    OrderChannel,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentStatus,
)
from app.auth.access import ALL_OUTLETS, Scope
from app.models.identity import Customer
from app.models.orders import Order, OrderItem
from app.models.payments import Payment, Transaction
from app.models.tenancy import DiningTable, Merchant, Outlet
from app.services import boundaries, org_tree


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
    service_option: str | None = None,
    created_by_user_id: str | None = None,
    source: str | None = None,
    external_id: str | None = None,
) -> Order:
    if not items:
        raise ConflictError("Order must contain at least one item", code="empty_order")

    outlet = _load_outlet(db, outlet_id)
    # Suspend enforcement: a suspended TENANT takes no orders on any channel (QR / cashier POS / app).
    # Storefront/chain-level suspend is checked per-stall in the item loop (cascade-aware).
    merchant = db.get(Merchant, outlet.merchant_id)
    if not merchant or not merchant.is_active:
        raise ConflictError("This store is currently unavailable", code="store_suspended")
    _checked_storefronts: set[str] = set()
    # QR ordering is gated by the merchant's `qr_ordering_enabled` module flag (Phase 2):
    # a rewards-only merchant accepts no customer QR orders. Staff/POS channels are unaffected.
    if channel == OrderChannel.QR and not boundaries.resolve_modules_for_outlet(
            db, outlet_id=outlet.id, merchant_id=outlet.merchant_id)["qr_ordering_enabled"]:
        raise ConflictError("Online ordering is not enabled here", code="ordering_disabled")
    # Resolve the fulfilment axes. On the QR (diner) channel the storefront's enabled SERVICE OPTIONS decide:
    # the diner picks one (auto if only one); it sets both order_type (dining context) AND hand_off. Other
    # channels (cashier/manual) keep the passed order_type + a `served` hand-off (staff hand it over).
    hand_off = HandOff.SERVED.value
    if channel == OrderChannel.QR:
        enabled = boundaries.resolve_service_options_for_outlet(db, outlet_id=outlet.id)
        key = service_option or (enabled[0] if enabled else DEFAULT_SERVICE_OPTIONS[0])
        if key not in enabled:
            raise ConflictError("That service option isn't offered here", code="service_option_unavailable")
        spec = SERVICE_OPTIONS[key]
        order_type = OrderType(spec["order_type"])
        hand_off = spec["hand_off"]
    order = Order(
        merchant_id=outlet.merchant_id,
        brand_id=outlet.brand_id,
        outlet_id=outlet.id,
        table_id=table_id,
        customer_id=customer_id,
        created_by_user_id=created_by_user_id,
        channel=channel.value,
        order_type=order_type.value,
        hand_off=hand_off,
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
        # Cascade-aware suspend check for the stall (Storefront node id == its Menu id) being ordered.
        category = db.get(MenuCategory, item.category_id)
        sf_id = category.menu_id if category else None
        if sf_id and sf_id not in _checked_storefronts:
            _checked_storefronts.add(sf_id)
            sf_node = org_tree.node_for(db, sf_id)
            if sf_node is not None and not org_tree.is_live(db, sf_node):
                raise ConflictError("This store is currently unavailable", code="store_suspended")

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


def advance_fulfilment(db: Session, order: Order, new_status: FulfilmentStatus) -> Order:
    """Advance the KITCHEN/ticket state (queued→preparing→ready→collected) — separate from payment.
    READY = ready for pick-up. Validated forward-only via FULFILMENT_TRANSITIONS."""
    current = FulfilmentStatus(order.fulfilment_status)
    if new_status not in FULFILMENT_TRANSITIONS[current]:
        raise ConflictError(
            f"Cannot move kitchen ticket from {current.value} to {new_status.value}",
            code="invalid_fulfilment_transition",
        )
    order.fulfilment_status = new_status.value
    db.flush()
    return order


def kitchen_ticket(db: Session, order: Order) -> dict:
    """Serialize ONE order as a KDS ticket (works whether or not it's still in the queue —
    used for the PATCH response after a COLLECTED move drops it from the list)."""
    customer = db.get(Customer, order.customer_id) if order.customer_id else None
    table = db.get(DiningTable, order.table_id) if order.table_id else None
    return {
        "id": order.id,
        "status": order.status,
        "fulfilment_status": order.fulfilment_status,
        "order_type": order.order_type,
        "hand_off": order.hand_off,
        "channel": order.channel,
        "created_at": order.created_at,
        "total": float(order.total),
        # KDS shows the order number, not PII — never expose the diner's phone to the kitchen.
        "customer_name": customer.full_name if customer else None,
        "table_label": table.label if table else None,
        "items": order.items,
    }


def list_kitchen_orders(db: Session, *, outlet_id: str, limit: int = 100) -> list[dict]:
    """The KDS queue for one outlet: PAID orders (`status=COMPLETED`) not yet COLLECTED, **oldest-first**
    (FIFO — the kitchen works the earliest ticket next). Items + table/customer labels + fulfilment_status."""
    stmt = (
        select(Order)
        .where(
            Order.outlet_id == outlet_id,
            Order.status == OrderStatus.COMPLETED.value,
            Order.fulfilment_status != FulfilmentStatus.COLLECTED.value,
        )
        .order_by(Order.created_at.asc())
        .limit(min(limit, 200))
    )
    return [kitchen_ticket(db, o) for o in db.scalars(stmt).all()]


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
    rewards_on = boundaries.resolve_modules_for_outlet(
        db, outlet_id=order.outlet_id, merchant_id=order.merchant_id)["rewards_enabled"]
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


@dataclass
class VoidResult:
    amount: Decimal
    points_reversed: int = 0
    voucher_restored: str | None = None


def void_order(db: Session, *, order: Order, reason: str = "") -> VoidResult:
    """Reverse a COMPLETED (paid) sale at the POS — supervisor action (`order.void`). Undoes every
    side-effect of checkout: removes the sales transaction (so it leaves all reports), voids the
    payment, reverses loyalty points earned (merchant + any coalition), and restores a voucher that
    was redeemed onto the order. Sets the order status to VOIDED. Idempotent-guarded."""
    from app.loyalty.engine import record_reward_txn
    from app.models.enums import RewardScope, RewardTxnType
    from app.models.loyalty import LoyaltyAccount, RewardRedemption, RewardTransaction

    if order.status == OrderStatus.VOIDED.value:
        raise ConflictError("Order already voided", code="already_voided")
    if order.status != OrderStatus.COMPLETED.value:
        raise ConflictError("Only a completed (paid) sale can be voided", code="not_voidable")

    amount = money(order.total)

    # 1) Reverse every loyalty EARN posted for this order (merchant + coalition), append-only:
    #    a negative ADJUST entry mirrors each earn and the cached balance is decremented.
    points_reversed = 0
    earns = db.scalars(
        select(RewardTransaction).where(
            RewardTransaction.order_id == order.id,
            RewardTransaction.txn_type == RewardTxnType.EARN.value,
        )
    ).all()
    for e in earns:
        acct = db.get(LoyaltyAccount, e.account_id)
        if acct is None or not e.points:
            continue
        record_reward_txn(db, account=acct, txn_type=RewardTxnType.ADJUST.value,
                          points=-e.points, reason=f"Void of order {order.id}", order_id=order.id)
        acct.points_balance -= e.points
        if acct.scope_type == RewardScope.MERCHANT.value and acct.scope_id == order.merchant_id:
            points_reversed += e.points

    # 2) Restore a voucher that was applied to this order (back to issued → reusable).
    voucher_restored: str | None = None
    if order.voucher_code:
        v = db.scalar(
            select(RewardRedemption).where(
                RewardRedemption.order_id == order.id,
                RewardRedemption.voucher_code == order.voucher_code,
                RewardRedemption.status == "redeemed",
            )
        )
        if v is not None:
            v.status = "issued"
            v.redeemed_at = None
            v.redeemed_by_user_id = None
            v.order_id = None
            voucher_restored = order.voucher_code

    # 3) Void the payment + remove the sales transaction so it drops out of revenue/RFM/reports.
    txn = db.scalar(select(Transaction).where(Transaction.order_id == order.id))
    if txn is not None:
        pay = db.get(Payment, txn.payment_id)
        if pay is not None:
            pay.status = PaymentStatus.VOIDED.value
        db.delete(txn)

    # 4) Mark the order voided (terminal). `reason` is captured by the caller's audit record.
    order.status = OrderStatus.VOIDED.value
    db.flush()
    return VoidResult(amount=amount, points_reversed=points_reversed, voucher_restored=voucher_restored)


def list_merchant_orders(
    db: Session,
    *,
    merchant_id: str,
    scope: Scope,
    status: str | None = None,
    outlet_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """The merchant-wide orders feed: orders for the merchant, newest first, with items +
    resolved outlet/customer/table labels. Tenant-scoped to the merchant; an outlet-limited
    user only sees their outlets'. Optional status / outlet filters."""
    stmt = select(Order).where(Order.merchant_id == merchant_id)

    allowed = scope.outlet_limit(merchant_id)
    allowed_set = None if allowed is ALL_OUTLETS else set(allowed)
    if outlet_id:
        allowed_set = {outlet_id} if allowed_set is None else (allowed_set & {outlet_id})
    if allowed_set is not None:
        if not allowed_set:
            return []  # outlet-scoped user with no matching outlet → nothing
        stmt = stmt.where(Order.outlet_id.in_(allowed_set))

    if status:
        stmt = stmt.where(Order.status == status)

    orders = db.scalars(stmt.order_by(Order.created_at.desc()).limit(min(limit, 200))).all()

    out: list[dict] = []
    for o in orders:
        outlet = db.get(Outlet, o.outlet_id)
        customer = db.get(Customer, o.customer_id) if o.customer_id else None
        table = db.get(DiningTable, o.table_id) if o.table_id else None
        out.append({
            "id": o.id,
            "status": o.status,
            "fulfilment_status": o.fulfilment_status,
            "hand_off": o.hand_off,
            "channel": o.channel,
            "created_at": o.created_at,
            "subtotal": float(o.subtotal),
            "service_charge": float(o.service_charge),
            "tax": float(o.tax),
            "total": float(o.total),
            "outlet_name": outlet.name if outlet else "—",
            "customer_name": (customer.full_name or customer.phone) if customer else None,
            "table_label": table.label if table else None,
            "items": o.items,
        })
    return out
