"""Platform-operator (super admin) service: ecosystem-wide aggregates,
merchant directory + KPIs, coalition overview, and merchant onboarding."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.enums import RewardRuleType, RewardScope, RoleName, ScopeType
from app.models.identity import Role, User, UserRoleAssignment
from app.models.loyalty import Coalition, LoyaltyAccount, RewardRule, coalition_members
from app.models.payments import Transaction
from app.models.tenancy import Brand, Merchant, Outlet
from app.services import merchant_settings
from app.services.boundaries import MODULE_FLAGS


def overview(db: Session) -> dict:
    gmv, orders, active_customers = db.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
            func.count(func.distinct(Transaction.customer_id)),
        )
    ).one()
    return {
        "gmv": round(float(gmv), 2),
        "orders": int(orders),
        "active_customers": int(active_customers),
        "merchants_total": db.scalar(select(func.count(Merchant.id))) or 0,
        "merchants_active": db.scalar(select(func.count(Merchant.id)).where(Merchant.is_active.is_(True))) or 0,
        "brands": db.scalar(select(func.count(Brand.id))) or 0,
        "outlets": db.scalar(select(func.count(Outlet.id))) or 0,
        "coalitions": db.scalar(select(func.count(Coalition.id))) or 0,
    }


def _merchant_owner(db: Session, merchant_id: str) -> User | None:
    return db.scalar(
        select(User)
        .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(
            Role.name == RoleName.MERCHANT_OWNER.value,
            UserRoleAssignment.scope_type == ScopeType.MERCHANT.value,
            UserRoleAssignment.scope_id == merchant_id,
        )
    )


def list_merchants(db: Session) -> list[dict]:
    out = []
    for m in db.scalars(select(Merchant).order_by(Merchant.created_at)).all():
        revenue, orders, customers = db.execute(
            select(
                func.coalesce(func.sum(Transaction.amount), 0),
                func.count(Transaction.id),
                func.count(func.distinct(Transaction.customer_id)),
            ).where(Transaction.merchant_id == m.id)
        ).one()
        owner = _merchant_owner(db, m.id)
        flags = {f: bool((m.settings or {}).get(f, merchant_settings.DEFAULTS[f])) for f in MODULE_FLAGS}
        out.append({
            "id": m.id,
            "name": m.name,
            "is_active": m.is_active,
            "brands": db.scalar(select(func.count(Brand.id)).where(Brand.merchant_id == m.id)) or 0,
            "outlets": db.scalar(select(func.count(Outlet.id)).where(Outlet.merchant_id == m.id)) or 0,
            "revenue": round(float(revenue), 2),
            "orders": int(orders),
            "customers": int(customers),
            "owner_email": owner.email if owner else None,
            "owner_name": (owner.full_name or owner.email) if owner else None,
            "module_flags": flags,
        })
    out.sort(key=lambda x: x["revenue"], reverse=True)
    return out


def list_coalitions(db: Session) -> list[dict]:
    out = []
    for c in db.scalars(select(Coalition)).all():
        member_ids = list(db.scalars(
            select(coalition_members.c.merchant_id).where(coalition_members.c.coalition_id == c.id)
        ).all())
        # Resolve names in the same order as member_ids so the two lists stay parallel.
        name_by_id = dict(db.execute(
            select(Merchant.id, Merchant.name).where(Merchant.id.in_(member_ids))
        ).all()) if member_ids else {}
        members = [name_by_id.get(mid, mid) for mid in member_ids]
        points = db.scalar(
            select(func.coalesce(func.sum(LoyaltyAccount.lifetime_points), 0)).where(
                LoyaltyAccount.scope_type == RewardScope.COALITION.value,
                LoyaltyAccount.scope_id == c.id,
            )
        ) or 0
        out.append({
            "id": c.id, "name": c.name, "is_active": c.is_active,
            "members": members, "member_ids": member_ids, "member_count": len(member_ids),
            "points_issued": int(points),
        })
    return out


def create_merchant(db: Session, *, name: str, owner_email: str, owner_password: str,
                    owner_name: str = "") -> dict:
    if db.scalar(select(User).where(User.email == owner_email)):
        raise ConflictError("A user with this email already exists", code="email_taken")
    role = db.scalar(select(Role).where(Role.name == RoleName.MERCHANT_OWNER.value))
    if not role:
        raise NotFoundError("merchant_owner role missing (run RBAC seed)", code="role_missing")

    merchant = Merchant(name=name)
    db.add(merchant)
    db.flush()
    brand = Brand(merchant_id=merchant.id, name=name)
    db.add(brand)
    db.flush()
    owner = User(email=owner_email, full_name=owner_name or owner_email,
                 password_hash=hash_password(owner_password))
    db.add(owner)
    db.flush()
    db.add(UserRoleAssignment(user_id=owner.id, role_id=role.id,
                              scope_type=ScopeType.MERCHANT.value, scope_id=merchant.id))
    # Sensible default so loyalty works out of the box.
    db.add(RewardRule(scope_type=RewardScope.MERCHANT.value, scope_id=merchant.id, code="base-earn",
                      rule_type=RewardRuleType.EARN_RATE.value, config={"points_per_dollar": 1}, is_active=True))
    db.flush()
    return {"merchant_id": merchant.id, "name": merchant.name,
            "owner_email": owner.email, "owner_user_id": owner.id}


def set_merchant_active(db: Session, *, merchant_id: str, is_active: bool) -> Merchant:
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise NotFoundError("Merchant not found", code="merchant_not_found")
    merchant.is_active = is_active
    db.flush()
    return merchant


def update_merchant(db: Session, *, merchant_id: str, name: str | None = None,
                    module_flags: dict[str, bool] | None = None) -> Merchant:
    """Operator-side merchant edit: rename and/or set module flags. Unknown flag keys rejected."""
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise NotFoundError("Merchant not found", code="merchant_not_found")
    if name is not None:
        merchant.name = name
    if module_flags:
        bad = set(module_flags) - set(MODULE_FLAGS)
        if bad:
            raise AppError(f"Unknown module flag(s): {', '.join(sorted(bad))}",
                           code="bad_module_flag", status_code=400)
        # Reuse the single source of truth for the settings JSON merge.
        merchant_settings.update_settings(db, merchant_id=merchant_id,
                                          changes={k: bool(v) for k, v in module_flags.items()})
    db.flush()
    return merchant


# ─── Platform operators (super admins) ──────────────────────────────────────
def _super_admin_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.name == RoleName.SUPER_ADMIN.value))
    if not role:
        raise NotFoundError("super_admin role missing (run RBAC seed)", code="role_missing")
    return role


def list_operators(db: Session, *, current_user_id: str = "") -> list[dict]:
    """All platform super admins (the people who can run the operator console)."""
    role = db.scalar(select(Role).where(Role.name == RoleName.SUPER_ADMIN.value))
    if not role:
        return []
    user_ids = db.scalars(
        select(UserRoleAssignment.user_id).where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.scope_type == ScopeType.PLATFORM.value,
        )
    ).all()
    out = []
    for uid in dict.fromkeys(user_ids):  # de-dup, preserve order
        u = db.get(User, uid)
        if not u:
            continue
        out.append({
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "is_active": u.is_active, "is_self": u.id == current_user_id,
        })
    out.sort(key=lambda x: x["email"])
    return out


def invite_operator(db: Session, *, email: str, password: str, full_name: str = "") -> User:
    """Create a new platform super admin (operator)."""
    role = _super_admin_role(db)
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("A user with this email already exists", code="email_taken")
    user = User(email=email, full_name=full_name or email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id,
                              scope_type=ScopeType.PLATFORM.value, scope_id=None))
    db.flush()
    return user


def revoke_operator(db: Session, *, operator_id: str, current_user_id: str) -> None:
    """Remove a user's platform super-admin grant. Guards: can't revoke yourself, and
    can't remove the last remaining operator (avoids locking everyone out of the console)."""
    if operator_id == current_user_id:
        raise ForbiddenError("You cannot revoke your own operator access", code="cannot_revoke_self")
    role = _super_admin_role(db)
    assignments = db.scalars(
        select(UserRoleAssignment).where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.scope_type == ScopeType.PLATFORM.value,
        )
    ).all()
    distinct_operators = {a.user_id for a in assignments}
    if operator_id not in distinct_operators:
        raise NotFoundError("Operator not found", code="operator_not_found")
    if len(distinct_operators) <= 1:
        raise ForbiddenError("Cannot remove the last platform operator", code="last_operator")
    for a in assignments:
        if a.user_id == operator_id:
            db.delete(a)
    db.flush()


# ─── Coalitions ─────────────────────────────────────────────────────────────
def _require_coalition(db: Session, coalition_id: str) -> Coalition:
    c = db.get(Coalition, coalition_id)
    if not c:
        raise NotFoundError("Coalition not found", code="coalition_not_found")
    return c


def create_coalition(db: Session, *, name: str) -> Coalition:
    c = Coalition(name=name)
    db.add(c)
    db.flush()
    return c


def update_coalition(db: Session, *, coalition_id: str, name: str | None = None,
                     is_active: bool | None = None) -> Coalition:
    c = _require_coalition(db, coalition_id)
    if name is not None:
        c.name = name
    if is_active is not None:
        c.is_active = is_active
    db.flush()
    return c


def add_coalition_member(db: Session, *, coalition_id: str, merchant_id: str) -> None:
    _require_coalition(db, coalition_id)
    if not db.get(Merchant, merchant_id):
        raise NotFoundError("Merchant not found", code="merchant_not_found")
    exists = db.scalar(
        select(func.count()).select_from(coalition_members).where(
            coalition_members.c.coalition_id == coalition_id,
            coalition_members.c.merchant_id == merchant_id,
        )
    )
    if exists:
        raise ConflictError("Merchant already in this coalition", code="already_member")
    db.execute(coalition_members.insert().values(coalition_id=coalition_id, merchant_id=merchant_id))
    db.flush()


def remove_coalition_member(db: Session, *, coalition_id: str, merchant_id: str) -> None:
    _require_coalition(db, coalition_id)
    result = db.execute(
        coalition_members.delete().where(
            coalition_members.c.coalition_id == coalition_id,
            coalition_members.c.merchant_id == merchant_id,
        )
    )
    if result.rowcount == 0:
        raise NotFoundError("Merchant is not a member of this coalition", code="not_member")
    db.flush()
