"""Customer rewards + wheel schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class MyProfileOut(ORMModel):
    full_name: str
    phone: str | None = None
    email: str | None = None
    birthday: date | None = None
    gender: str | None = None


class ProfileUpdate(BaseModel):
    phone: str | None = None
    birthday: date | None = None
    gender: str | None = None
    full_name: str | None = None


class MyOrderOut(ORMModel):
    id: str
    status: str
    total: float
    items_count: int
    summary: str
    outlet_name: str | None = None
    created_at: datetime


class MyVoucherOut(ORMModel):
    voucher_code: str
    reward_name: str
    status: str
    created_at: datetime


class RewardTxnOut(ORMModel):
    txn_type: str
    points: int
    reason: str
    created_at: datetime


class LoyaltySummaryOut(BaseModel):
    points_balance: int
    lifetime_points: int
    tier: str
    next_tier: str | None = None
    points_to_next_tier: int
    visit_count: int
    recent: list[RewardTxnOut] = []


class CatalogItemOut(BaseModel):
    id: str
    name: str
    description: str
    cost_points: int
    kind: str
    value: float
    can_afford: bool | None = None


class RedeemRequest(BaseModel):
    merchant_id: str
    item_id: str


class RedeemResponse(BaseModel):
    voucher_code: str
    reward_name: str
    points_balance: int


class WheelSegmentOut(BaseModel):
    label: str
    color: str


class WheelConfigOut(BaseModel):
    spin_cost: int
    segments: list[WheelSegmentOut]


class SpinRequest(BaseModel):
    merchant_id: str


class PrizeOut(BaseModel):
    kind: str
    label: str
    points: int = 0
    voucher_code: str | None = None


class SpinResponse(BaseModel):
    winning_index: int
    prize: PrizeOut
    points_balance: int
    spin_cost: int


# --- 3x3 Jackpot ---------------------------------------------------------
class JackpotPrizeOut(BaseModel):
    item_name: str
    item_price: float
    emoji: str
    weight: int


class JackpotConfigOut(BaseModel):
    spin_cost: int
    grid_size: int
    payline: str  # "middle_row"
    grand_prize: int  # progressive pot (persistent; resets to base on a win)
    prizes: list[JackpotPrizeOut]


class JackpotCellOut(BaseModel):
    item_name: str
    item_price: float
    emoji: str


class JackpotWinOut(BaseModel):
    item_name: str
    item_price: float
    emoji: str
    voucher_code: str


class JackpotPlayOut(BaseModel):
    spin_cost: int
    grid: list[list[JackpotCellOut]]
    won: bool
    prize: JackpotWinOut | None = None
    points_balance: int
