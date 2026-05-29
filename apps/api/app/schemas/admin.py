"""User-management (admin) schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RoleAssignmentOut(BaseModel):
    assignment_id: str
    role: str
    scope_type: str
    scope_id: str | None = None


class AdminUserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[RoleAssignmentOut] = []


class InviteUserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=160)
    role: str = Field(pattern="^(merchant_owner|brand_manager|outlet_manager|staff)$")
    scope_type: str = Field(pattern="^(merchant|brand|outlet)$")
    scope_id: str | None = None


class InviteUserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
