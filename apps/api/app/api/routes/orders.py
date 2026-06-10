"""Ordering routes — QR/customer path + cashier/staff path + status lifecycle + checkout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_customer, get_scope, require, resolve_merchant
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.enums import OrderChannel, OrderStatus, PaymentMethod
from app.models.identity import Customer
from app.models.orders import Order
from app.models.tenancy import Outlet
from app.schemas.orders import (
    CheckoutRequest,
    CheckoutResponse,
    FulfilmentStatusUpdate,
    KitchenOrderOut,
    ManualOrderCreate,
    MerchantOrderOut,
    OrderOut,
    OrderStatusUpdate,
    PaymentOut,
    QrOrderCreate,
    VoidOrderIn,
    VoidResponse,
)
from app.schemas.pos import ReceiptOut
from app.services import orders as orders_service
from app.services import qr as qr_service
from app.services import receipts
from app.services.audit import record as audit_record
from app.services.orders import OrderItemInput

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_inputs(items) -> list[OrderItemInput]:
    return [
        OrderItemInput(menu_item_id=i.menu_item_id, quantity=i.quantity, modifier_ids=i.modifier_ids)
        for i in items
    ]


# --- Staff: merchant-wide orders feed ----------------------------------
@router.get("", response_model=list[MerchantOrderOut])
def list_orders(
    merchant_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    outlet_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    scope=Depends(get_scope),
    db: Session = Depends(get_db),
):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "order.view", mid)
    return orders_service.list_merchant_orders(
        db, merchant_id=mid, scope=scope, status=status, outlet_id=outlet_id, limit=limit
    )


# --- Kitchen display (KDS): the paid, not-yet-collected queue for one outlet -----------------
@router.get("/kitchen", response_model=list[KitchenOrderOut])
def kitchen_orders(
    outlet_id: str = Query(...),
    scope=Depends(get_scope),
    db: Session = Depends(get_db),
):
    outlet = db.get(Outlet, outlet_id)
    if not outlet:
        raise NotFoundError("Outlet not found", code="outlet_not_found")
    require(scope, "order.view", outlet.merchant_id)
    if not scope.can_view_outlet(outlet.merchant_id, outlet.id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")
    return orders_service.list_kitchen_orders(db, outlet_id=outlet_id)


# --- Kitchen display (KDS): advance a ticket (queued→preparing→ready→collected) --------------
@router.patch("/{order_id}/fulfilment", response_model=KitchenOrderOut)
def advance_fulfilment(
    order_id: str, body: FulfilmentStatusUpdate, scope=Depends(get_scope), db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found", code="order_not_found")
    require(scope, "order.manage", order.merchant_id)
    if not scope.can_view_outlet(order.merchant_id, order.outlet_id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")
    orders_service.advance_fulfilment(db, order, body.status)
    audit_record(db, action="order.fulfilment_change", actor_id=scope.user_id,
                 merchant_id=order.merchant_id, entity_type="order", entity_id=order.id,
                 meta={"fulfilment_status": body.status.value})
    db.commit()
    db.refresh(order)
    return orders_service.kitchen_ticket(db, order)


# --- Customer QR order -------------------------------------------------
@router.post("", response_model=OrderOut, status_code=201)
def create_qr_order(
    body: QrOrderCreate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    qr = qr_service.resolve_token(db, body.qr_token)
    order = orders_service.create_order(
        db, outlet_id=qr.outlet_id, items=_to_inputs(body.items),
        customer_id=customer.id, table_id=qr.table_id,
        channel=OrderChannel.QR, order_type=body.order_type,
    )
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


# --- Cashier / manual order (hybrid model) -----------------------------
@router.post("/manual", response_model=OrderOut, status_code=201)
def create_manual_order(
    body: ManualOrderCreate,
    scope=Depends(get_scope),
    db: Session = Depends(get_db),
):
    outlet = db.get(Outlet, body.outlet_id)
    if not outlet:
        raise NotFoundError("Outlet not found", code="outlet_not_found")
    require(scope, "order.manage", outlet.merchant_id)
    if not scope.can_view_outlet(outlet.merchant_id, outlet.id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")

    customer_id = None
    if body.customer_phone:
        customer = db.scalar(select(Customer).where(Customer.phone == body.customer_phone))
        if not customer:
            customer = Customer(phone=body.customer_phone)
            db.add(customer)
            db.flush()
        customer_id = customer.id

    order = orders_service.create_order(
        db, outlet_id=outlet.id, items=_to_inputs(body.items),
        customer_id=customer_id, table_id=body.table_id,
        channel=OrderChannel.CASHIER, order_type=body.order_type,
        created_by_user_id=scope.user_id,
    )
    audit_record(db, action="order.create_manual", actor_id=scope.user_id,
                 merchant_id=outlet.merchant_id, entity_type="order", entity_id=order.id)
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


# --- Customer: view own order ------------------------------------------
@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order or order.customer_id != customer.id:
        raise NotFoundError("Order not found", code="order_not_found")
    return OrderOut.model_validate(order)


# --- Staff: advance order status ---------------------------------------
@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: str, body: OrderStatusUpdate, scope=Depends(get_scope), db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found", code="order_not_found")
    require(scope, "order.manage", order.merchant_id)
    if not scope.can_view_outlet(order.merchant_id, order.outlet_id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")
    orders_service.update_status(db, order, body.status)
    audit_record(db, action="order.status_change", actor_id=scope.user_id,
                 merchant_id=order.merchant_id, entity_type="order", entity_id=order.id,
                 meta={"status": body.status.value})
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


# --- Customer checkout (QR path) ---------------------------------------
@router.post("/{order_id}/checkout", response_model=CheckoutResponse)
def customer_checkout(
    order_id: str, body: CheckoutRequest,
    customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if not order or order.customer_id != customer.id:
        raise NotFoundError("Order not found", code="order_not_found")
    result = orders_service.checkout(db, order=order, method=PaymentMethod(body.method.value),
                                     force_outcome=body.force_outcome)
    db.commit()
    db.refresh(result.payment)
    return CheckoutResponse(
        payment=PaymentOut.model_validate(result.payment),
        transaction_id=result.transaction.id if result.transaction else None,
        points_earned=result.points_earned,
        order_id=order.id,
    )


# --- Cashier checkout (walk-in path) -----------------------------------
@router.post("/{order_id}/cashier-checkout", response_model=CheckoutResponse)
def cashier_checkout(
    order_id: str, body: CheckoutRequest, scope=Depends(get_scope), db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found", code="order_not_found")
    require(scope, "payment.process", order.merchant_id)
    if not scope.can_view_outlet(order.merchant_id, order.outlet_id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")
    result = orders_service.checkout(db, order=order, method=PaymentMethod(body.method.value),
                                     force_outcome=body.force_outcome)
    audit_record(db, action="payment.process", actor_id=scope.user_id,
                 merchant_id=order.merchant_id, entity_type="payment", entity_id=result.payment.id)
    db.commit()
    db.refresh(result.payment)
    return CheckoutResponse(
        payment=PaymentOut.model_validate(result.payment),
        transaction_id=result.transaction.id if result.transaction else None,
        points_earned=result.points_earned,
        order_id=order.id,
    )


# --- Void a paid sale (POS, supervisor) --------------------------------
@router.post("/{order_id}/void", response_model=VoidResponse)
def void_order(order_id: str, body: VoidOrderIn, scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Reverse a completed (paid) sale — requires `order.void` (Supervisor+). Undoes the transaction,
    payment, loyalty points, and any voucher; sets the order to VOIDED."""
    order = db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found", code="order_not_found")
    require(scope, "order.void", order.merchant_id)
    if not scope.can_view_outlet(order.merchant_id, order.outlet_id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")
    result = orders_service.void_order(db, order=order, reason=body.reason)
    audit_record(db, action="order.void", actor_id=scope.user_id, merchant_id=order.merchant_id,
                 entity_type="order", entity_id=order.id,
                 meta={"reason": body.reason, "amount": float(result.amount),
                       "points_reversed": result.points_reversed,
                       "voucher_restored": result.voucher_restored})
    db.commit()
    return VoidResponse(order_id=order.id, status=OrderStatus.VOIDED.value, amount=float(result.amount),
                        points_reversed=result.points_reversed, voucher_restored=result.voucher_restored)


# --- Receipt (POS) -----------------------------------------------------
@router.get("/{order_id}/receipt", response_model=ReceiptOut)
def order_receipt(order_id: str, scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Printable receipt payload — company header (console) + outlet/stall + lines + payment."""
    order = db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found", code="order_not_found")
    require(scope, "order.view", order.merchant_id)
    if not scope.can_view_outlet(order.merchant_id, order.outlet_id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")
    return ReceiptOut(**receipts.build_receipt(db, order=order))
