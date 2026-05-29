"""Auth request/response schemas (Pydantic v2)."""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


class _PhoneMixin:
    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v):  # type: ignore[no-untyped-def]
        if v is not None and not _PHONE_RE.match(v):
            raise ValueError("phone must be 7-15 digits, optional leading +")
        return v


class CustomerRegisterRequest(BaseModel, _PhoneMixin):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=160)
    phone: str | None = None
    birthday: date | None = None


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class OtpRequest(BaseModel, _PhoneMixin):
    phone: str


class OtpVerifyRequest(BaseModel, _PhoneMixin):
    phone: str
    code: str = Field(min_length=4, max_length=8)
    full_name: str = Field(default="", max_length=160)


class SsoLoginRequest(BaseModel):
    provider: Literal["google", "apple"]
    sub: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    full_name: str = Field(default="", max_length=160)


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class CustomerOut(ORMModel):
    id: str
    email: EmailStr | None = None
    phone: str | None = None
    full_name: str
    birthday: date | None = None


class UserOut(ORMModel):
    id: str
    email: EmailStr
    full_name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    actor: Literal["customer", "user"]
    customer: CustomerOut | None = None
    user: UserOut | None = None


class OtpRequestResponse(BaseModel):
    message: str
    # dev/mock only: present so the demo + tests can complete without real SMS
    debug_code: str | None = None
