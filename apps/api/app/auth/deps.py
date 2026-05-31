"""FastAPI dependencies: extract + verify the current customer/user from a JWT,
resolve back-office scope, and a `require(...)` permission guard."""
from __future__ import annotations

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.auth.access import Scope, resolve_scope
from app.core.errors import AppError, AuthError, ForbiddenError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.identity import Customer, User


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing or malformed Authorization header", code="missing_token")
    return authorization.split(" ", 1)[1].strip()


def _decode(token: str) -> dict:
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid token", code="invalid_token") from exc
    if payload.get("type") != "access":
        raise AuthError("Not an access token", code="invalid_token")
    return payload


def get_current_customer(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Customer:
    payload = _decode(_bearer(authorization))
    if payload.get("actor") != "customer":
        raise ForbiddenError("Customer token required", code="wrong_actor")
    customer = db.get(Customer, payload.get("sub"))
    if not customer or not customer.is_active:
        raise AuthError("Customer not found", code="not_found")
    return customer


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    payload = _decode(_bearer(authorization))
    if payload.get("actor") != "user":
        raise ForbiddenError("Staff token required", code="wrong_actor")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise AuthError("User not found", code="not_found")
    return user


def get_scope(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scope:
    return resolve_scope(db, user)


def require(scope: Scope, permission: str, merchant_id: str | None = None) -> None:
    """Raise ForbiddenError unless `scope` grants `permission` (optionally within merchant)."""
    if not scope.can(permission, merchant_id):
        raise ForbiddenError(f"Missing permission: {permission}", code="forbidden")


def require_super_admin(scope: Scope = Depends(get_scope)) -> Scope:
    """Dependency: only the Platform Super Admin / Owner (wildcard) may proceed."""
    if not scope.is_super_admin:
        raise ForbiddenError("Platform operator access required", code="forbidden")
    return scope


def require_platform(permission: str):
    """Dependency factory: require a specific platform-tier permission (operator roles).
    The Owner (super_admin wildcard) always passes; other operator roles pass iff they
    hold `permission` at platform scope."""
    def _dep(scope: Scope = Depends(get_scope)) -> Scope:
        if scope.is_super_admin or permission in scope.platform_perms:
            return scope
        raise ForbiddenError(f"Missing platform permission: {permission}", code="forbidden")
    return _dep


def resolve_merchant(scope: Scope, merchant_id: str | None) -> str:
    """Resolve which merchant a back-office request targets, enforcing access.

    - super admin: must pass merchant_id explicitly.
    - merchant-scoped user: defaults to their (single) merchant; any explicit
      merchant_id must be one they can access.
    """
    # Owner (wildcard) or a platform operator with drill-in may target any merchant explicitly.
    if scope.is_super_admin or scope.platform_drilldown:
        if not merchant_id:
            raise AppError("merchant_id is required", code="merchant_required", status_code=400)
        return merchant_id
    accessible = scope.accessible_merchant_ids
    if merchant_id:
        if merchant_id not in accessible:
            raise ForbiddenError("No access to this merchant", code="forbidden")
        return merchant_id
    if len(accessible) == 1:
        return next(iter(accessible))
    raise AppError("Specify merchant_id", code="merchant_required", status_code=400)
