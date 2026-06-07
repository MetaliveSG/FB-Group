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
    # Platform-tier operator permissions (granular operator roles):
    "platform.overview.view": "View ecosystem overview/KPIs",
    "platform.merchants.view": "View the merchant directory + coalitions",
    "platform.merchants.onboard": "Onboard + edit merchants (not suspend)",
    "platform.merchants.suspend": "Suspend/activate merchants",
    "platform.coalitions.manage": "Create/edit coalitions + membership",
    "platform.merchant.access": "Drill into a merchant (operator view)",
    "platform.operators.manage": "Invite/revoke platform operators",
    "merchant.manage": "Manage merchant account settings",
    "brand.manage": "Manage brands",
    "outlet.manage": "Manage outlets, tables, QR codes",
    "org.manage": "Build the org tree — create/rename nodes at any depth (enterprise→stall)",
    "menu.manage": "Manage menus, items, modifiers",
    "order.view": "View orders",
    "order.manage": "Create/update orders + status",
    "order.void": "Void/cancel a completed order or line (supervisor+)",
    "payment.process": "Process checkout/payments",
    "crm.view": "View CRM customers + analytics",
    "crm.manage": "Manage tags, notes, segments",
    "campaign.manage": "Create/run campaigns",
    "report.view": "View sales reports + forecasts",
    "user.manage": "Invite users, assign/revoke roles",
    "audit.view": "View audit logs",
}
WILDCARD = "*"

# Platform permissions that imply a "managing" (write) operator — used to decide whether a
# drill-in is full-access or read-only (see access.py).
PLATFORM_WRITE_PERMS = {
    "platform.merchants.onboard", "platform.merchants.suspend", "platform.coalitions.manage",
}
# Merchant-tier "view" permissions a read-only operator may exercise on drill-in.
DRILLDOWN_READ_PERMS = {"crm.view", "report.view", "order.view", "audit.view"}

# --- Role -> permission matrix -----------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleName.SUPER_ADMIN.value: [WILDCARD],  # Platform Owner
    RoleName.PLATFORM_ADMIN.value: [
        "platform.overview.view", "platform.merchants.view", "platform.merchants.onboard",
        "platform.merchants.suspend", "platform.coalitions.manage", "platform.merchant.access",
    ],
    RoleName.PLATFORM_ONBOARDER.value: [
        "platform.overview.view", "platform.merchants.view", "platform.merchants.onboard",
    ],
    RoleName.PLATFORM_SUPPORT.value: [
        "platform.overview.view", "platform.merchants.view", "platform.merchant.access",
    ],
    # Enterprise (group) tier — bundles assigned at an Enterprise node, cascading over the group.
    RoleName.GROUP_CEO.value: [
        "merchant.manage", "brand.manage", "outlet.manage", "org.manage", "menu.manage",
        "order.view", "order.manage", "order.void", "payment.process", "crm.view", "crm.manage",
        "campaign.manage", "report.view", "user.manage", "audit.view",
    ],
    RoleName.GROUP_COO.value: [
        "brand.manage", "outlet.manage", "org.manage", "menu.manage", "order.view", "order.manage",
        "order.void", "payment.process", "crm.view", "crm.manage", "campaign.manage", "report.view",
    ],
    RoleName.GROUP_CFO.value: ["report.view", "audit.view", "crm.view"],   # finance (read)
    RoleName.GROUP_ACCOUNTANT.value: ["report.view", "audit.view"],        # finance (read-only)
    RoleName.MERCHANT_OWNER.value: [
        "merchant.manage", "brand.manage", "outlet.manage", "org.manage", "menu.manage",
        "order.view", "order.manage", "order.void", "payment.process", "crm.view", "crm.manage",
        "campaign.manage", "report.view", "user.manage", "audit.view",
    ],
    RoleName.BRAND_MANAGER.value: [
        "brand.manage", "outlet.manage", "org.manage", "menu.manage", "order.view", "order.manage",
        "crm.view", "report.view",
    ],
    RoleName.AREA_MANAGER.value: [
        "outlet.manage", "org.manage", "menu.manage", "order.view", "order.manage", "crm.view",
        "report.view",
    ],
    RoleName.OUTLET_MANAGER.value: [
        "outlet.manage", "org.manage", "menu.manage", "order.view", "order.manage",
        "payment.process", "crm.view", "report.view",
    ],
    RoleName.STALL_OPERATOR.value: [
        "order.view", "order.manage", "payment.process", "menu.manage",
    ],
    RoleName.STAFF.value: ["order.view", "order.manage", "payment.process"],
    # Member-tree role PALETTE (Chain/Storefront). Assigned at any node; node sets the reach.
    RoleName.MANAGER.value: [
        "merchant.manage", "brand.manage", "outlet.manage", "org.manage", "menu.manage",
        "order.view", "order.manage", "order.void", "payment.process", "crm.view", "crm.manage",
        "campaign.manage", "report.view", "user.manage", "audit.view",
    ],
    RoleName.CASHIER.value: ["order.view", "order.manage", "payment.process"],
    RoleName.FINANCE.value: ["report.view"],   # web read-only: REPORTS ONLY
    RoleName.VIEWER.value: ["crm.view", "order.view", "audit.view"],  # web read-only: everything EXCEPT reports
    # POS-only on-floor lead (Supervisor): cashier verbs + store reports + the supervisor-only power
    # to VOID a transaction (the key differentiator from Cashier). Deliberately NOT org/menu/staff/
    # merchant management (those are web MANAGER/OWNER) — distinct from the web "Manager" role.
    RoleName.SUPERVISOR.value: ["order.view", "order.manage", "order.void", "payment.process", "report.view"],
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
