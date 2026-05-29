"""Permission catalog + role->permission matrix + RBAC seeding.

Least-privilege by design. `super_admin` holds the wildcard "*".
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RoleName
from app.models.identity import Permission, Role

# --- Permission codes ---------------------------------------------------
P = {
    "platform.manage": "Manage the whole platform",
    "merchant.manage": "Manage merchant account settings",
    "brand.manage": "Manage brands",
    "outlet.manage": "Manage outlets, tables, QR codes",
    "menu.manage": "Manage menus, items, modifiers",
    "order.view": "View orders",
    "order.manage": "Create/update orders + status",
    "payment.process": "Process checkout/payments",
    "crm.view": "View CRM customers + analytics",
    "crm.manage": "Manage tags, notes, segments",
    "campaign.manage": "Create/run campaigns",
    "report.view": "View sales reports + forecasts",
    "user.manage": "Invite users, assign/revoke roles",
    "audit.view": "View audit logs",
}
WILDCARD = "*"

# --- Role -> permission matrix -----------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleName.SUPER_ADMIN.value: [WILDCARD],
    RoleName.MERCHANT_OWNER.value: [
        "merchant.manage", "brand.manage", "outlet.manage", "menu.manage",
        "order.view", "order.manage", "payment.process", "crm.view", "crm.manage",
        "campaign.manage", "report.view", "user.manage", "audit.view",
    ],
    RoleName.BRAND_MANAGER.value: [
        "brand.manage", "outlet.manage", "menu.manage", "order.view", "order.manage",
        "crm.view", "report.view",
    ],
    RoleName.OUTLET_MANAGER.value: [
        "outlet.manage", "menu.manage", "order.view", "order.manage", "payment.process",
        "crm.view", "report.view",
    ],
    RoleName.STAFF.value: ["order.view", "order.manage", "payment.process"],
    RoleName.CUSTOMER.value: [],
}


def seed_rbac(db: Session) -> dict[str, Role]:
    """Idempotently create permissions + roles + links. Returns roles by name."""
    perms: dict[str, Permission] = {}
    for code, desc in P.items():
        perm = db.scalar(select(Permission).where(Permission.code == code))
        if not perm:
            perm = Permission(code=code, description=desc)
            db.add(perm)
        perms[code] = perm
    db.flush()

    roles: dict[str, Role] = {}
    for role_name, codes in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(name=role_name, description=f"{role_name} role")
            db.add(role)
            db.flush()
        if codes == [WILDCARD]:
            role.permissions = list(perms.values())
        else:
            role.permissions = [perms[c] for c in codes]
        roles[role_name] = role
    db.flush()
    return roles
