"""POS schemas — receipt payload (company header + outlet/stall + lines + payment)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReceiptCompany(BaseModel):
    name: str
    uen: str = ""
    address: str = ""
    phone: str = ""


class ReceiptOutlet(BaseModel):
    name: str
    address: str = ""


class ReceiptItem(BaseModel):
    name: str
    quantity: int
    line_total: float
    modifiers: list[str] = []


class ReceiptPayment(BaseModel):
    method: str
    status: str
    reference: str | None = None


class ReceiptOut(BaseModel):
    company: ReceiptCompany
    outlet: ReceiptOutlet
    stall: str | None = None
    order_id: str
    table_label: str | None = None
    created_at: datetime
    items: list[ReceiptItem]
    subtotal: float
    service_charge: float
    tax: float
    discount: float
    voucher_code: str | None = None
    total: float
    payment: ReceiptPayment | None = None
    points_earned: int | None = None
    footer: str
