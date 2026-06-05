"""Auth routes: customer (password / OTP / SSO-mock) + staff login + token refresh.

Rate limiting guards OTP issuance and login against brute force/abuse.
"""
from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.deps import get_current_customer
from app.core.config import settings
from app.core.errors import AuthError, RateLimitedError
from app.core.rate_limit import rate_limiter
from app.core.security import decode_token
from app.db.session import get_db
from app.schemas.auth import (
    ConsentUpdateRequest,
    CustomerLoginRequest,
    CustomerOut,
    CustomerRegisterRequest,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    PinLoginRequest,
    RefreshRequest,
    SsoLoginRequest,
    StaffLoginRequest,
    TokenResponse,
    UserOut,
)
from app.services import consent as consent_service
from app.services import vouchers as voucher_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limit(key: str, limit: int) -> None:
    if not rate_limiter.hit(key, limit):
        raise RateLimitedError("Too many requests — please slow down", code="rate_limited")


def _issue_welcome(db: Session, customer, merchant_id: str | None) -> None:
    """Best-effort welcome voucher pack (idempotent) AFTER the signup is committed — a rewards
    hiccup must never block login/signup."""
    if not merchant_id:
        return
    try:
        voucher_service.issue_welcome_pack(db, customer_id=customer.id, merchant_id=merchant_id)
        db.commit()
    except Exception:  # best-effort: roll back the pack, keep the (already-committed) signup
        db.rollback()


def _customer_token(customer) -> TokenResponse:
    toks = auth_service.issue_tokens(customer.id, "customer")
    return TokenResponse(actor="customer", customer=CustomerOut.model_validate(customer), **toks)


# --- Customer: email + password ----------------------------------------
@router.post("/customer/register", response_model=TokenResponse, status_code=201)
def customer_register(body: CustomerRegisterRequest, request: Request, db: Session = Depends(get_db)):
    customer = auth_service.register_customer_password(
        db, email=body.email, password=body.password, full_name=body.full_name,
        phone=body.phone, birthday=body.birthday,
        accepted_terms=body.accepted_terms, marketing_opt_in=body.marketing_opt_in,
        consent_merchant_id=body.consent_merchant_id, ip=_client_ip(request),
    )
    db.commit()
    _issue_welcome(db, customer, body.consent_merchant_id)
    return _customer_token(customer)


@router.post("/customer/login", response_model=TokenResponse)
def customer_login(body: CustomerLoginRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(f"login:{_client_ip(request)}:{body.email}", settings.RATE_LIMIT_LOGIN_PER_MIN)
    customer = auth_service.login_customer_password(db, email=body.email, password=body.password)
    return _customer_token(customer)


# --- Customer: mobile OTP ----------------------------------------------
@router.post("/customer/otp/request", response_model=OtpRequestResponse)
def otp_request(body: OtpRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(f"otp:{body.phone}", settings.RATE_LIMIT_OTP_PER_MIN)
    code = auth_service.request_otp(db, phone=body.phone)
    return OtpRequestResponse(
        message="OTP sent (mock provider)",
        debug_code=code if settings.DEBUG else None,
    )


@router.post("/customer/otp/verify", response_model=TokenResponse)
def otp_verify(body: OtpVerifyRequest, request: Request, db: Session = Depends(get_db)):
    customer = auth_service.verify_otp_login(
        db, phone=body.phone, code=body.code, full_name=body.full_name,
        accepted_terms=body.accepted_terms, marketing_opt_in=body.marketing_opt_in,
        consent_merchant_id=body.consent_merchant_id, ip=_client_ip(request),
    )
    db.commit()
    _issue_welcome(db, customer, body.consent_merchant_id)
    return _customer_token(customer)


# --- Customer: SSO mock ------------------------------------------------
@router.post("/customer/sso", response_model=TokenResponse)
def customer_sso(body: SsoLoginRequest, request: Request, db: Session = Depends(get_db)):
    customer = auth_service.sso_login(
        db, provider=body.provider, sub=body.sub, email=body.email, full_name=body.full_name,
        accepted_terms=body.accepted_terms, marketing_opt_in=body.marketing_opt_in,
        consent_merchant_id=body.consent_merchant_id, ip=_client_ip(request),
    )
    db.commit()
    _issue_welcome(db, customer, body.consent_merchant_id)
    return _customer_token(customer)


# --- Customer: PDPA consent withdrawal / update (authenticated) --------
@router.post("/customer/consent", response_model=CustomerOut)
def update_consent(body: ConsentUpdateRequest, request: Request,
                   customer=Depends(get_current_customer), db: Session = Depends(get_db)):
    """Grant or WITHDRAW marketing consent (PDPA withdrawal right) — records an audit event."""
    consent_service.set_marketing(db, customer=customer, merchant_id=body.merchant_id,
                                  granted=body.marketing_opt_in, source="profile", ip=_client_ip(request))
    db.commit()
    db.refresh(customer)
    return CustomerOut.model_validate(customer)


# --- Staff login -------------------------------------------------------
@router.post("/staff/login", response_model=TokenResponse)
def staff_login(body: StaffLoginRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(f"login:{_client_ip(request)}:{body.email}", settings.RATE_LIMIT_LOGIN_PER_MIN)
    user = auth_service.login_user(db, email=body.email, password=body.password)
    toks = auth_service.issue_tokens(user.id, "user")
    return TokenResponse(actor="user", user=UserOut.model_validate(user), **toks)


# --- Staff POS PIN login ----------------------------------------------
@router.post("/staff/pin-login", response_model=TokenResponse)
def staff_pin_login(body: PinLoginRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(f"pin:{_client_ip(request)}:{body.merchant_id}", settings.RATE_LIMIT_LOGIN_PER_MIN)
    user = auth_service.pin_login(db, merchant_id=body.merchant_id, pin=body.pin)
    toks = auth_service.issue_tokens(user.id, "user")
    return TokenResponse(actor="user", user=UserOut.model_validate(user), **toks)


# --- Token refresh -----------------------------------------------------
@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Refresh token expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid refresh token", code="invalid_token") from exc
    if payload.get("type") != "refresh":
        raise AuthError("Not a refresh token", code="invalid_token")
    actor = payload.get("actor", "customer")
    toks = auth_service.issue_tokens(payload["sub"], actor)
    return TokenResponse(actor=actor, **toks)
