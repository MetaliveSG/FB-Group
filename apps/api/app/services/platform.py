"""Platform-operator (super admin) service: ecosystem-wide aggregates,
merchant directory + KPIs, coalition overview, and merchant onboarding."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.enums import RewardRuleType, RewardScope, RoleName, ScopeType
from app.models.identity import Role, User, UserRoleAssignment
from app.models.loyalty import Coalition, LoyaltyAccount, RewardRule, coalition_members
from app.models.payments import Transaction
from app.models.tenancy import Brand, Merchant, Outlet


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
        })
    out.sort(key=lambda x: x["revenue"], reverse=True)
    return out


def list_coalitions(db: Session) -> list[dict]:
    out = []
    for c in db.scalars(select(Coalition)).all():
        member_ids = db.scalars(
            select(coalition_members.c.merchant_id).where(coalition_members.c.coalition_id == c.id)
        ).all()
        members = db.scalars(select(Merchant.name).where(Merchant.id.in_(member_ids))).all()
        points = db.scalar(
            select(func.coalesce(func.sum(LoyaltyAccount.lifetime_points), 0)).where(
                LoyaltyAccount.scope_type == RewardScope.COALITION.value,
                LoyaltyAccount.scope_id == c.id,
            )
        ) or 0
        out.append({
            "id": c.id, "name": c.name, "is_active": c.is_active,
            "members": list(members), "member_count": len(member_ids),
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
