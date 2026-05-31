"""Org-structure (brands/outlets/tables) schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


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


class SettingsOut(BaseModel):
    pipeline_enabled: bool
    wheel_spin_cost: int
    jackpot_spin_cost: int
    # Module-adoption flags (Phase 2) — which parts of the suite this merchant runs.
    rewards_enabled: bool = True
    qr_ordering_enabled: bool = True
    pos_enabled: bool = False


class NavFlagsOut(BaseModel):
    """Minimal, non-sensitive UI toggles any staff member may read to render nav —
    deliberately omits economic config (spin costs, earn rates). Full settings stay
    owner-only (`merchant.manage`); these "which features the venue runs" booleans are
    already public (the anonymous QR context exposes rewards/ordering to diners)."""
    pipeline_enabled: bool
    rewards_enabled: bool = True
    qr_ordering_enabled: bool = True
    pos_enabled: bool = False


class SettingsUpdateIn(BaseModel):
    pipeline_enabled: bool | None = None
    # Spin costs bounded both ends: 0 = free play; upper cap keeps a typo from setting
    # an absurd cost (only affects the merchant's own games, but keeps data sane).
    wheel_spin_cost: int | None = Field(default=None, ge=0, le=100000)
    jackpot_spin_cost: int | None = Field(default=None, ge=0, le=100000)
    rewards_enabled: bool | None = None
    qr_ordering_enabled: bool | None = None
    pos_enabled: bool | None = None


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
