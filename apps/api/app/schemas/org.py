"""Org-structure (brands/outlets/tables) schemas."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.analytics.timezones import require_tz
from app.core.passwords import validate_password_strength


class BrandOut(BaseModel):
    id: str
    name: str
    cuisine_type: str | None = None
    is_active: bool
    outlets: int


class BrandCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    cuisine_type: str | None = Field(default=None, max_length=80)


class BrandUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    cuisine_type: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class OutletOut(BaseModel):
    id: str
    name: str
    address: str | None = None
    is_active: bool
    brand_id: str
    brand_name: str | None = None
    tables: int
    menu_id: str | None = None


class OutletCreateIn(BaseModel):
    brand_id: str
    name: str = Field(min_length=1, max_length=160)
    address: str | None = Field(default=None, max_length=255)


class OutletUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class TableOut(BaseModel):
    id: str
    label: str
    seats: int
    is_active: bool
    qr_token: str | None = None


class WelcomeVoucherCfg(BaseModel):
    """Welcome voucher pack granted on signup (the "10× $1, one per day" campaign). Stored in
    merchants.settings; issued by services/vouchers.issue_welcome_pack on registration."""
    enabled: bool = False
    count: int = Field(default=1, ge=1, le=100)
    value: float = Field(default=0, ge=0)
    per_period: Literal["day", "week", "month"] | None = None
    valid_days: int | None = Field(default=None, ge=1, le=3650)
    name: str = Field(default="Welcome voucher", max_length=120)


class SettingsOut(BaseModel):
    pipeline_enabled: bool
    wheel_spin_cost: int
    jackpot_spin_cost: int
    # Module-adoption flags (Phase 2) — which parts of the suite this merchant runs.
    rewards_enabled: bool = True
    qr_ordering_enabled: bool = True
    pos_enabled: bool = False
    # The tenant's canonical reporting timezone (the "books" — payouts/GST/daily close use it).
    timezone: str = "Asia/Singapore"
    welcome_voucher: WelcomeVoucherCfg = Field(default_factory=WelcomeVoucherCfg)


class NavFlagsOut(BaseModel):
    """Minimal, non-sensitive UI toggles any staff member may read to render nav —
    deliberately omits economic config (spin costs, earn rates). Full settings stay
    owner-only (`merchant.manage`); these "which features the venue runs" booleans are
    already public (the anonymous QR context exposes rewards/ordering to diners).

    `can_manage_merchant` is the caller's capability (holds `merchant.manage` → owner or
    operator), so the client can hide owner-only nav (Settings / Team) without a second call."""
    pipeline_enabled: bool
    rewards_enabled: bool = True
    qr_ordering_enabled: bool = True
    pos_enabled: bool = False
    can_manage_merchant: bool = False


class MyPermissionsOut(BaseModel):
    """The caller's effective permission codes in a merchant context — the capabilities
    contract that drives client-side nav rendering. `permissions` is expanded (never the
    raw '*' wildcard); `is_super_admin` short-circuits to "can do everything"."""
    permissions: list[str]
    is_super_admin: bool = False


class SettingsUpdateIn(BaseModel):
    pipeline_enabled: bool | None = None
    # Spin costs bounded both ends: 0 = free play; upper cap keeps a typo from setting
    # an absurd cost (only affects the merchant's own games, but keeps data sane).
    wheel_spin_cost: int | None = Field(default=None, ge=0, le=100000)
    jackpot_spin_cost: int | None = Field(default=None, ge=0, le=100000)
    rewards_enabled: bool | None = None
    qr_ordering_enabled: bool | None = None
    pos_enabled: bool | None = None
    timezone: str | None = None   # IANA reporting timezone for this tenant; validated → 422 on bad
    welcome_voucher: WelcomeVoucherCfg | None = None

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, v: str | None) -> str | None:
        return require_tz(v) if v is not None else v


class LoyaltyProgramOut(BaseModel):
    points_per_dollar: float
    welcome_bonus: int
    birthday_bonus: int


class LoyaltyProgramUpdateIn(BaseModel):
    # 0 disables a rule. Bounded to keep a typo from minting absurd balances.
    points_per_dollar: float = Field(ge=0, le=1000)
    welcome_bonus: int = Field(ge=0, le=1_000_000)
    birthday_bonus: int = Field(ge=0, le=1_000_000)


class TableCreateIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    seats: int = Field(default=4, ge=1, le=50)


# --- Member tree: Chain / Storefront (any depth) -----------------------
class OrgNodeOut(BaseModel):
    """One node of the member-tree, flat (the client assembles the tree via `parent_id`).
    `role` is CHAIN or STOREFRONT; `sells` is the engine truth. `can_manage` = whether THIS
    caller may create/rename beneath it (downline-only)."""
    id: str
    parent_id: str | None = None
    role: str                       # CHAIN | STOREFRONT
    name: str | None = None
    depth: int
    sells: bool
    chain_stopped: bool = False     # a Chain whose children may only be Storefronts
    is_settlement_boundary: bool = False  # this Chain is a tenant ("merchant")
    subscription_fee: Decimal | None = None  # per-node SaaS fee (NULL = inherit parent)
    is_active: bool
    can_manage: bool = False
    qr_path: str | None = None      # customer-scan path: a Storefront → /t/{token}; a Chain → /t/node/{id}; None if unscannable
    outlet_id: str | None = None    # a Storefront's typed Outlet (menu.id==node.id → outlet) — lets the console scope to it; None for a Chain


class OrgTreeOut(BaseModel):
    """The caller's visible slice of the member-tree + whether they can grow it at all."""
    nodes: list[OrgNodeOut]
    can_manage: bool = False


class OrgNodeCreateIn(BaseModel):
    parent_id: str
    role: str = Field(description="CHAIN (structural) | STOREFRONT (sells, leaf)")
    name: str = Field(min_length=1, max_length=120)
    chain_stopped: bool = False     # only meaningful for a CHAIN
    subscription_fee: Decimal | None = Field(default=None, ge=0)


class OrgNodeUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None
    chain_stopped: bool | None = None
    subscription_fee: Decimal | None = Field(default=None, ge=0)


# --- Node logins (staff assigned at a member-tree node) ----------------
class NodeAccountOut(BaseModel):
    assignment_id: str
    user_id: str
    email: EmailStr
    full_name: str
    is_active: bool
    role: str                       # manager | cashier | staff | finance


class NodeAccountCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=160)
    role: str = Field(pattern="^(manager|cashier|staff|finance)$")

    _pw = field_validator("password")(validate_password_strength)


# --- Leases (venue↔stall tenancy edge — foodcourt GTO vs coffeeshop FIXED) ----
class LeaseOut(BaseModel):
    """One tenancy at a venue. `rent_type` is the foodcourt/coffeeshop switch: FIXED = flat $/mo
    (landlord blind); GTO = % of turnover (landlord reads turnover). `rate` is $/mo for FIXED, a
    percentage for GTO."""
    id: str
    venue_id: str
    tenant_node_id: str
    tenant_name: str | None = None
    rent_type: str                  # FIXED | GTO
    rate: Decimal
    is_active: bool


class LeaseCreateIn(BaseModel):
    tenant_node_id: str
    rent_type: str = Field(pattern="^(FIXED|GTO)$")
    rate: Decimal = Field(ge=0)


class LeaseUpdateIn(BaseModel):
    rent_type: str | None = Field(default=None, pattern="^(FIXED|GTO)$")
    rate: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
