"""Resolve a back-office user's effective scope + permissions for tenant isolation.

A user holds role assignments at platform / merchant / brand / outlet scope.
We resolve those into:
  - which merchants they can touch,
  - which outlets within each merchant they're limited to (ALL = no limit),
  - which permission codes apply per merchant.

Data queries then filter by these; endpoint guards check `can(...)`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import ROLE_PERMISSIONS, WILDCARD
from app.models.enums import RoleName, ScopeType
from app.models.identity import User
from app.models.tenancy import Brand, Outlet


class _All:
    """Sentinel: no outlet restriction within a merchant."""

    def __repr__(self) -> str:  # pragma: no cover
        return "ALL"


ALL_OUTLETS = _All()


@dataclass
class Scope:
    user_id: str = ""
    is_super_admin: bool = False
    platform_perms: set[str] = field(default_factory=set)
    merchant_perms: dict[str, set[str]] = field(default_factory=dict)
    merchant_outlets: dict[str, object] = field(default_factory=dict)  # mid -> set[str] | ALL_OUTLETS

    def _perms_for(self, merchant_id: str | None) -> set[str]:
        perms = set(self.platform_perms)
        if merchant_id and merchant_id in self.merchant_perms:
            perms |= self.merchant_perms[merchant_id]
        return perms

    def can(self, permission: str, merchant_id: str | None = None) -> bool:
        if self.is_super_admin:
            return True
        perms = self._perms_for(merchant_id)
        return WILDCARD in perms or permission in perms

    @property
    def accessible_merchant_ids(self) -> set[str]:
        return set(self.merchant_perms.keys())

    def outlet_limit(self, merchant_id: str):
        """Returns ALL_OUTLETS or a set of outlet ids the user is restricted to."""
        if self.is_super_admin:
            return ALL_OUTLETS
        return self.merchant_outlets.get(merchant_id, set())

    def can_view_outlet(self, merchant_id: str, outlet_id: str) -> bool:
        if self.is_super_admin:
            return True
        limit = self.outlet_limit(merchant_id)
        return limit is ALL_OUTLETS or outlet_id in limit


def resolve_scope(db: Session, user: User) -> Scope:
    scope = Scope(user_id=user.id)
    for a in user.role_assignments:
        role_name = a.role.name
        perms = set(ROLE_PERMISSIONS.get(role_name, []))

        if a.scope_type == ScopeType.PLATFORM.value:
            scope.platform_perms |= perms
            if role_name == RoleName.SUPER_ADMIN.value or WILDCARD in perms:
                scope.is_super_admin = True
            continue

        merchant_id: str | None = None
        outlets: object = ALL_OUTLETS

        if a.scope_type == ScopeType.MERCHANT.value:
            merchant_id = a.scope_id
            outlets = ALL_OUTLETS
        elif a.scope_type == ScopeType.BRAND.value:
            brand = db.get(Brand, a.scope_id) if a.scope_id else None
            if not brand:
                continue
            merchant_id = brand.merchant_id
            outlets = set(db.scalars(select(Outlet.id).where(Outlet.brand_id == brand.id)).all())
        elif a.scope_type == ScopeType.OUTLET.value:
            outlet = db.get(Outlet, a.scope_id) if a.scope_id else None
            if not outlet:
                continue
            merchant_id = outlet.merchant_id
            outlets = {outlet.id}

        if not merchant_id:
            continue

        scope.merchant_perms.setdefault(merchant_id, set()).update(perms)
        existing = scope.merchant_outlets.get(merchant_id)
        if existing is ALL_OUTLETS or outlets is ALL_OUTLETS:
            scope.merchant_outlets[merchant_id] = ALL_OUTLETS
        else:
            scope.merchant_outlets[merchant_id] = (existing or set()) | outlets  # type: ignore[operator]

    return scope
