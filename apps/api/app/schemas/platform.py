"""Operator (platform super admin) schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class OverviewOut(BaseModel):
    gmv: float
    orders: int
    active_customers: int
    merchants_total: int
    merchants_active: int
    brands: int
    outlets: int
    coalitions: int


class MerchantKpiOut(BaseModel):
    id: str
    name: str
    is_active: bool
    brands: int
    outlets: int
    revenue: float
    orders: int
    customers: int
    owner_email: str | None = None
    owner_name: str | None = None


class CoalitionOut(BaseModel):
    id: str
    name: str
    is_active: bool
    members: list[str] = []
    member_count: int
    points_issued: int


class MerchantCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)
    owner_name: str = Field(default="", max_length=160)


class MerchantCreateOut(BaseModel):
    merchant_id: str
    name: str
    owner_email: EmailStr
    owner_user_id: str


class MerchantActiveIn(BaseModel):
    is_active: bool
