"""Order + checkout schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import FulfilmentStatus, OrderStatus, OrderType, PaymentMethod
from app.schemas.common import ORMModel, UtcDatetime


class OrderItemInputSchema(BaseModel):
    menu_item_id: str
    quantity: int = Field(default=1, ge=1, le=99)
    modifier_ids: list[str] = []


class QrOrderCreate(BaseModel):
    qr_token: str
    items: list[OrderItemInputSchema] = Field(min_length=1)
    order_type: OrderType = OrderType.DINE_IN          # legacy; superseded by service_option on the QR path
    service_option: str | None = None                  # the diner's chosen service option (key); auto if one


class ManualOrderCreate(BaseModel):
    outlet_id: str
    items: list[OrderItemInputSchema] = Field(min_length=1)
    table_id: str | None = None
    customer_phone: str | None = None
    order_type: OrderType = OrderType.DINE_IN


class OrderItemOut(ORMModel):
    id: str
    name_snapshot: str
    unit_price: float
    quantity: int
    modifiers: list | None = []
    line_total: float


class OrderOut(ORMModel):
    id: str
    merchant_id: str
    brand_id: str
    outlet_id: str
    table_id: str | None = None
    customer_id: str | None = None
    channel: str
    order_type: str
    hand_off: str = "served"            # self_pickup (diner collects + alert) | served (waiter brings it)
    status: str
    fulfilment_status: str = "queued"   # kitchen/pick-up state — lets the diner track "ready for pick-up"
    subtotal: float
    service_charge: float
    tax: float
    total: float
    items: list[OrderItemOut] = []


class MerchantOrderOut(BaseModel):
    """Row in the merchant-wide orders feed — order + items + resolved labels."""
    id: str
    status: str
    fulfilment_status: str = FulfilmentStatus.QUEUED.value
    hand_off: str = "served"
    channel: str
    created_at: UtcDatetime
    subtotal: float
    service_charge: float
    tax: float
    total: float
    outlet_name: str
    customer_name: str | None = None
    table_label: str | None = None
    items: list[OrderItemOut] = []


class KitchenOrderOut(BaseModel):
    """One ticket on the kitchen display (KDS) — a paid, not-yet-collected order for the outlet."""
    id: str
    status: str
    fulfilment_status: str
    order_type: str
    hand_off: str = "served"
    channel: str
    created_at: UtcDatetime
    total: float
    customer_name: str | None = None
    table_label: str | None = None
    items: list[OrderItemOut] = []


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class FulfilmentStatusUpdate(BaseModel):
    status: FulfilmentStatus


class CheckoutRequest(BaseModel):
    method: PaymentMethod
    force_outcome: Literal["success", "fail"] | None = None


class PaymentOut(ORMModel):
    id: str
    method: str
    amount: float
    status: str
    reference: str | None = None
    failure_reason: str | None = None


class CheckoutResponse(BaseModel):
    payment: PaymentOut
    transaction_id: str | None = None
    points_earned: int = 0
    order_id: str


class VoidOrderIn(BaseModel):
    reason: str = Field(default="", max_length=200)


class VoidResponse(BaseModel):
    order_id: str
    status: str
    amount: float
    points_reversed: int = 0          # merchant coins clawed back from the diner
    voucher_restored: str | None = None  # a voucher code made reusable again, if any
