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


class SettingsUpdateIn(BaseModel):
    pipeline_enabled: bool | None = None
    wheel_spin_cost: int | None = Field(default=None, ge=0)
    jackpot_spin_cost: int | None = Field(default=None, ge=0)


class TableCreateIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    seats: int = Field(default=4, ge=1, le=50)
