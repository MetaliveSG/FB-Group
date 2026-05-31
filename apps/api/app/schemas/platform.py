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
    # The three adoption module flags (Phase 0c) — manageable from the operator side.
    module_flags: dict = {}


class MerchantUpdateIn(BaseModel):
    """Operator-side merchant edits: rename and/or flip module flags. All optional."""
    name: str | None = Field(default=None, min_length=1, max_length=160)
    module_flags: dict[str, bool] | None = None


class CoalitionOut(BaseModel):
    id: str
    name: str
    is_active: bool
    members: list[str] = []
    member_ids: list[str] = []  # parallel to `members`, for membership management
    member_count: int
    points_issued: int


class CoalitionCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class CoalitionUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None


class CoalitionMemberIn(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=32)


class OperatorOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_self: bool = False  # the currently-authenticated operator (can't revoke own access)


class OperatorCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=160)


class OperatorCreateOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None


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
