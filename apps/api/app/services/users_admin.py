"""User management — invite users, assign scoped roles, revoke (Module 10)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.enums import RoleName, ScopeType
from app.models.identity import Role, User, UserRoleAssignment
from app.models.tenancy import Brand, Outlet

# Roles a merchant admin (owner) is allowed to grant. Never super_admin / platform.
GRANTABLE_ROLES = {
    RoleName.MERCHANT_OWNER.value, RoleName.BRAND_MANAGER.value,
    RoleName.OUTLET_MANAGER.value, RoleName.STAFF.value,
}


def _merchant_scope_ids(db: Session, merchant_id: str) -> set[str]:
    brand_ids = db.scalars(select(Brand.id).where(Brand.merchant_id == merchant_id)).all()
    outlet_ids = db.scalars(select(Outlet.id).where(Outlet.merchant_id == merchant_id)).all()
    return {merchant_id} | set(brand_ids) | set(outlet_ids)


def _validate_scope(db: Session, merchant_id: str, scope_type: str, scope_id: str | None) -> None:
    if scope_type == ScopeType.PLATFORM.value:
        raise ForbiddenError("Cannot grant platform scope", code="scope_forbidden")
    if scope_type == ScopeType.MERCHANT.value:
        if scope_id != merchant_id:
            raise ForbiddenError("Scope outside your merchant", code="scope_forbidden")
    elif scope_type == ScopeType.BRAND.value:
        b = db.get(Brand, scope_id) if scope_id else None
        if not b or b.merchant_id != merchant_id:
            raise ForbiddenError("Brand not in your merchant", code="scope_forbidden")
    elif scope_type == ScopeType.OUTLET.value:
        o = db.get(Outlet, scope_id) if scope_id else None
        if not o or o.merchant_id != merchant_id:
            raise ForbiddenError("Outlet not in your merchant", code="scope_forbidden")
    else:
        raise AppError("Invalid scope_type", code="bad_scope", status_code=400)


def list_users(db: Session, *, merchant_id: str) -> list[dict]:
    sids = _merchant_scope_ids(db, merchant_id)
    assignments = db.scalars(select(UserRoleAssignment).where(UserRoleAssignment.scope_id.in_(sids))).all()
    by_user: dict[str, list[UserRoleAssignment]] = {}
    for a in assignments:
        by_user.setdefault(a.user_id, []).append(a)
    out = []
    for uid, asgs in by_user.items():
        u = db.get(User, uid)
        if not u:
            continue
        roles = [{
            "assignment_id": a.id,
            "role": (db.get(Role, a.role_id).name if db.get(Role, a.role_id) else "?"),
            "scope_type": a.scope_type, "scope_id": a.scope_id,
        } for a in asgs]
        out.append({"id": u.id, "email": u.email, "full_name": u.full_name,
                    "is_active": u.is_active, "roles": roles})
    out.sort(key=lambda x: x["email"])
    return out


def invite_user(db: Session, *, merchant_id: str, email: str, password: str, full_name: str,
                role: str, scope_type: str, scope_id: str | None) -> User:
    if role not in GRANTABLE_ROLES:
        raise ForbiddenError("Role cannot be granted", code="role_not_allowed")
    _validate_scope(db, merchant_id, scope_type, scope_id)
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("A user with this email already exists", code="email_taken")
    role_obj = db.scalar(select(Role).where(Role.name == role))
    if not role_obj:
        raise NotFoundError("Role not found", code="role_missing")
    user = User(email=email, full_name=full_name or email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role_obj.id,
                              scope_type=scope_type, scope_id=scope_id))
    db.flush()
    return user


def revoke_assignment(db: Session, *, merchant_id: str, assignment_id: str) -> None:
    a = db.get(UserRoleAssignment, assignment_id)
    if not a:
        raise NotFoundError("Assignment not found", code="assignment_not_found")
    if a.scope_id not in _merchant_scope_ids(db, merchant_id):
        raise ForbiddenError("Assignment outside your merchant", code="forbidden")
    db.delete(a)
    db.flush()
