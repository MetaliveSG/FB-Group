"""Voucher redemption schemas (staff/cashier)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class VoucherRedeemIn(BaseModel):
    order_id: str | None = None   # apply the voucher's value to this order (the bill being settled)
    merchant_id: str | None = None  # required only when no order_id (operator drill-in)


class VoucherRedeemOut(BaseModel):
    voucher_code: str
    reward_name: str
    value: Decimal
    status: str
    order_id: str | None = None
    discount_amount: Decimal | None = None
    order_total: Decimal | None = None


class VoucherPreviewOut(BaseModel):
    """Dry-run validation (cashier checks before applying)."""
    voucher_code: str
    reward_name: str
    value: Decimal
    min_spend: Decimal
    valid_until: datetime | None = None
    valid: bool = True
