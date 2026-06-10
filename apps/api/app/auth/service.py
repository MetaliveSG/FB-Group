"""Authentication service: customer (password/OTP/SSO-mock) + staff login,
duplicate prevention, account linking, token issuance."""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.otp import otp_store
from app.core.config import settings
from app.core.errors import AuthError, ConflictError, ForbiddenError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.enums import AuthProvider
from app.models.identity import Customer, CustomerAuthIdentity, User
from app.services import consent


# --- Token helpers ------------------------------------------------------
def issue_tokens(subject: str, actor: str, claims: dict | None = None) -> dict:
    extra = {"actor": actor}
    if claims:
        extra.update(claims)
    # Customers (diners) get a 1-week access token so a meal/checkout isn't cut short; staff stay short.
    ttl = settings.CUSTOMER_TOKEN_EXPIRE_MINUTES if actor == "customer" else None
    return {
        "access_token": create_access_token(subject, extra, ttl_minutes=ttl),
        "refresh_token": create_refresh_token(subject, {"actor": actor}),
        "token_type": "bearer",
    }


# --- Customer identity helpers -----------------------------------------
def _find_customer_by_contact(db: Session, *, email: str | None, phone: str | None) -> Customer | None:
    if not email and not phone:
        return None
    conds = []
    if email:
        conds.append(Customer.email == email)
    if phone:
        conds.append(Customer.phone == phone)
    return db.scalar(select(Customer).where(or_(*conds)))


def _get_identity(db: Session, provider: str, identifier: str) -> CustomerAuthIdentity | None:
    return db.scalar(
        select(CustomerAuthIdentity).where(
            CustomerAuthIdentity.provider == provider,
            CustomerAuthIdentity.identifier == identifier,
        )
    )


# --- Customer: email + password ----------------------------------------
def register_customer_password(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str = "",
    phone: str | None = None,
    birthday: date | None = None,
    accepted_terms: bool = False,
    marketing_opt_in: bool = False,
    consent_merchant_id: str | None = None,
    ip: str | None = None,
) -> Customer:
    if _get_identity(db, AuthProvider.PASSWORD.value, email):
        raise ConflictError("An account with this email already exists", code="email_taken")
    if db.scalar(select(Customer).where(Customer.email == email)):
        raise ConflictError("Email already registered", code="email_taken")
    if phone and db.scalar(select(Customer).where(Customer.phone == phone)):
        raise ConflictError("Phone already registered", code="phone_taken")

    customer = Customer(email=email, phone=phone, full_name=full_name, birthday=birthday)
    db.add(customer)
    db.flush()
    # PDPA: capture consent AT the moment we create the PII record (raises if terms not accepted).
    consent.capture_signup_consent(db, customer=customer, merchant_id=consent_merchant_id,
                                   accepted_terms=accepted_terms, marketing_opt_in=marketing_opt_in,
                                   source="register", ip=ip)
    db.add(
        CustomerAuthIdentity(
            customer_id=customer.id,
            provider=AuthProvider.PASSWORD.value,
            identifier=email,
            secret_hash=hash_password(password),
            is_verified=True,
        )
    )
    db.flush()
    return customer


def login_customer_password(db: Session, *, email: str, password: str) -> Customer:
    identity = _get_identity(db, AuthProvider.PASSWORD.value, email)
    if not identity or not identity.secret_hash or not verify_password(password, identity.secret_hash):
        raise AuthError("Invalid email or password", code="invalid_credentials")
    return db.get(Customer, identity.customer_id)


# --- Customer: mobile OTP (register-or-login) --------------------------
def request_otp(db: Session, *, phone: str) -> str:
    return otp_store.issue(phone)  # returns code (dev/mock)


def verify_otp_login(db: Session, *, phone: str, code: str, full_name: str = "",
                     accepted_terms: bool = False, marketing_opt_in: bool = False,
                     consent_merchant_id: str | None = None, ip: str | None = None) -> Customer:
    if not otp_store.verify(phone, code):
        raise AuthError("Invalid or expired OTP", code="invalid_otp")
    # Find existing customer by phone (account linking), else create.
    customer = db.scalar(select(Customer).where(Customer.phone == phone))
    if not customer:
        customer = Customer(phone=phone, full_name=full_name)
        db.add(customer)
        db.flush()
        # PDPA: a NEW diner → capture consent at this first PII collection (raises if terms not accepted).
        consent.capture_signup_consent(db, customer=customer, merchant_id=consent_merchant_id,
                                       accepted_terms=accepted_terms, marketing_opt_in=marketing_opt_in,
                                       source="qr_signup", ip=ip)
    if not _get_identity(db, AuthProvider.MOBILE_OTP.value, phone):
        db.add(
            CustomerAuthIdentity(
                customer_id=customer.id,
                provider=AuthProvider.MOBILE_OTP.value,
                identifier=phone,
                is_verified=True,
            )
        )
        db.flush()
    return customer


# --- Customer: SSO (mock Google/Apple) ---------------------------------
def sso_login(db: Session, *, provider: str, sub: str, email: str | None = None, full_name: str = "",
              accepted_terms: bool = False, marketing_opt_in: bool = False,
              consent_merchant_id: str | None = None, ip: str | None = None) -> Customer:
    """Mock SSO: in production `sub`/`email` come from a verified provider token.

    Links to an existing customer by email if present (account linking).
    """
    if provider not in (AuthProvider.GOOGLE.value, AuthProvider.APPLE.value):
        raise AuthError("Unsupported SSO provider", code="bad_provider")
    identity = _get_identity(db, provider, sub)
    if identity:
        return db.get(Customer, identity.customer_id)

    customer = _find_customer_by_contact(db, email=email, phone=None)
    if not customer:
        customer = Customer(email=email, full_name=full_name)
        db.add(customer)
        db.flush()
        consent.capture_signup_consent(db, customer=customer, merchant_id=consent_merchant_id,
                                       accepted_terms=accepted_terms, marketing_opt_in=marketing_opt_in,
                                       source="sso", ip=ip)
    elif email and not customer.email:
        customer.email = email
    db.add(
        CustomerAuthIdentity(
            customer_id=customer.id, provider=provider, identifier=sub, is_verified=True
        )
    )
    db.flush()
    return customer


# --- Staff / back-office user login ------------------------------------
def login_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    # POS accounts (kind="pos") are PIN-only till operators — they have a locked password and may
    # NEVER use the web dashboard. Reject generically (no account-kind enumeration).
    if not user or user.kind == "pos" or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password", code="invalid_credentials")
    # Suspend enforcement: a merchant-staff (non-operator) whose every merchant is suspended cannot log
    # in. Operators (super_admin / platform roles) are always allowed — they manage + un-suspend.
    from app.auth.access import resolve_scope
    from app.models.tenancy import Merchant

    scope = resolve_scope(db, user)
    if not scope.is_super_admin and not scope.platform_perms:
        mids = scope.accessible_merchant_ids
        if mids and not db.scalar(
            select(Merchant.id).where(Merchant.id.in_(mids), Merchant.is_active.is_(True))
        ):
            raise ForbiddenError("Account suspended — contact the platform operator",
                                 code="account_suspended")
    return user


def pin_login(db: Session, *, merchant_id: str, pin: str, outlet_id: str | None = None) -> User:
    """POS quick-login: resolve the till operator whose PIN matches. PINs are unique **per storefront**,
    so the bound outlet scopes resolution (and the bcrypt fan-out). Suspend-aware."""
    from app.models.tenancy import Merchant
    from app.services import pos_staff

    m = db.get(Merchant, merchant_id)
    if m is None or not m.is_active:
        raise ForbiddenError("This store is unavailable", code="account_suspended")
    node = pos_staff.node_for_outlet(db, outlet_id) if outlet_id else None
    if node is None:
        raise AuthError("This till is not set up for PIN login", code="pos_not_provisioned")
    from app.services import boundaries
    if not boundaries.resolve_modules(db, node=node, merchant_id=merchant_id)["pos_enabled"]:
        raise ForbiddenError("POS is disabled for this store", code="pos_disabled")
    user = pos_staff.resolve_pos_pin(db, node_id=node.id, pin=pin)
    if user is None:
        raise AuthError("Invalid PIN", code="invalid_pin")
    return user
