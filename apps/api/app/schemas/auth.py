"""Auth request/response schemas (Pydantic v2)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.phone import to_e164
from app.schemas.common import ORMModel

_REGION_RE = "^(SG|MY|ID|TH)$"


class _PhoneMixin:
    """Normalize `phone` → canonical E.164 using the `region` field (default SG).
    Subclasses that carry a phone should declare a `region: str` field. National
    trunk prefixes are handled correctly (e.g. MY '016…' → '+6016…')."""

    @model_validator(mode="after")
    def _normalize_phone(self):  # type: ignore[no-untyped-def]
        if getattr(self, "phone", None) is not None:
            self.phone = to_e164(self.phone, getattr(self, "region", "SG") or "SG")
        return self


class _ConsentMixin(BaseModel):
    """PDPA consent captured at signup. `accepted_terms` (notice acknowledgement) is required to
    create an account; `marketing_opt_in` is express opt-in (default off). `consent_merchant_id` =
    the data-controller (loyalty domain) resolved from the QR context, recorded in the audit trail."""
    accepted_terms: bool = False
    marketing_opt_in: bool = False
    consent_merchant_id: str | None = None


class CustomerRegisterRequest(_ConsentMixin, _PhoneMixin):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=160)
    phone: str | None = None
    region: str = Field(default="SG", pattern=_REGION_RE)
    birthday: date | None = None


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class OtpRequest(BaseModel, _PhoneMixin):
    phone: str
    region: str = Field(default="SG", pattern=_REGION_RE)


class OtpVerifyRequest(_ConsentMixin, _PhoneMixin):
    phone: str
    region: str = Field(default="SG", pattern=_REGION_RE)
    code: str = Field(min_length=4, max_length=8)
    full_name: str = Field(default="", max_length=160)


class SsoLoginRequest(_ConsentMixin):
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
    marketing_consent: bool = False


class ConsentUpdateRequest(BaseModel):
    """Grant or withdraw marketing consent (the PDPA withdrawal path), from the customer profile."""
    marketing_opt_in: bool
    merchant_id: str | None = None


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
