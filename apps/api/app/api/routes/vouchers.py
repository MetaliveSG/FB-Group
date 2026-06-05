"""Voucher redemption (staff/cashier): validate + redeem-at-till. See docs/architecture-vouchers.md."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.orders import Order
from app.schemas.vouchers import VoucherPreviewOut, VoucherRedeemIn, VoucherRedeemOut
from app.services import vouchers as voucher_service

router = APIRouter(prefix="/vouchers", tags=["vouchers"])


def _merchant_for(db: Session, scope, order: Order | None, merchant_id: str | None) -> str:
    return order.merchant_id if order is not None else resolve_merchant(scope, merchant_id)


@router.get("/{code}", response_model=VoucherPreviewOut)
def preview_voucher(code: str, merchant_id: str | None = Query(None), order_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Dry-run: validate a scanned/typed voucher (no mutation) so the cashier can confirm before applying."""
    order = db.get(Order, order_id) if order_id else None
    if order_id and order is None:
        raise NotFoundError("Order not found", code="order_not_found")
    mid = _merchant_for(db, scope, order, merchant_id)
    require(scope, "order.view", mid)
    node_ids = voucher_service.order_storefront_nodes(db, order) if order else None
    v = voucher_service.validate_voucher(db, code=code, merchant_id=mid,
                                         order_total=(order.total if order else None),
                                         redeeming_node_ids=node_ids)
    return VoucherPreviewOut(voucher_code=v.voucher_code, reward_name=v.reward_name, value=v.value,
                             min_spend=v.min_spend, valid_until=v.valid_until, valid=True)


@router.post("/{code}/redeem", response_model=VoucherRedeemOut)
def redeem_voucher(code: str, body: VoucherRedeemIn, scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Cashier redeems a voucher (scan QR / enter code) → marks it used + applies its value to the order."""
    order = db.get(Order, body.order_id) if body.order_id else None
    if body.order_id and order is None:
        raise NotFoundError("Order not found", code="order_not_found")
    mid = _merchant_for(db, scope, order, body.merchant_id)
    require(scope, "order.manage", mid)
    v = voucher_service.redeem_voucher(db, code=code, merchant_id=mid,
                                       staff_user_id=scope.user_id, order=order)
    db.commit()
    return VoucherRedeemOut(
        voucher_code=v.voucher_code, reward_name=v.reward_name, value=v.value, status=v.status,
        order_id=(order.id if order else None),
        discount_amount=(order.discount_amount if order else None),
        order_total=(order.total if order else None),
    )
