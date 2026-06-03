"""Operator (platform super admin) schemas."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


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


# The four operator (platform-tier) roles a login can hold.
OPERATOR_ROLES = ("super_admin", "platform_admin", "platform_onboarder", "platform_support")


class OperatorOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    role: str = "super_admin"  # one of OPERATOR_ROLES
    is_self: bool = False  # the currently-authenticated operator (can't revoke own access)


class OperatorCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=160)
    # Which operator role to grant. Defaults to the workhorse Admin (not the all-powerful Owner).
    role: str = Field(default="platform_admin")

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        if v not in OPERATOR_ROLES:
            raise ValueError(f"role must be one of {OPERATOR_ROLES}")
        return v


class OperatorCreateOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    role: str = "platform_admin"


class PlatformCapabilitiesOut(BaseModel):
    """The operator's platform-tier capabilities — drives operator-console section/action gating."""
    permissions: list[str]
    is_owner: bool = False


class MerchantCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)
    owner_name: str = Field(default="", max_length=160)
    # Member-tree kind for the new top-level tenant: "chain" (drillable structure) or
    # "storefront" (a single operating unit). Plus its per-node SaaS subscription fee.
    kind: str = Field(default="chain")
    subscription_fee: Decimal | None = Field(default=None, ge=0)


class MerchantCreateOut(BaseModel):
    merchant_id: str
    name: str
    owner_email: EmailStr
    owner_user_id: str


class MerchantActiveIn(BaseModel):
    is_active: bool
