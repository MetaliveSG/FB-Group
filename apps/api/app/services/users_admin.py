"""Member-tree node-account web logins + POS staff PINs."""
from __future__ import annotations

import re

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.enums import RoleName, ScopeType
from app.models.identity import Role, User, UserRoleAssignment
from app.models.org import OrgNode

_PIN_RE = re.compile(r"^\d{4,6}$")

# The member-tree role palette — granted at a NODE (the caller's downline is enforced by the route
# via org_tree.can_manage_node, so no merchant scope-id validation is needed here).
# Roles grantable to a WEB/dashboard node login: Manager (full), Viewer (read all except reports),
# Finance (reports only). "cashier"/"supervisor" are excluded — POS-only PIN roles (see pos_staff.py).
NODE_GRANTABLE_ROLES = {
    RoleName.MANAGER.value, RoleName.VIEWER.value, RoleName.FINANCE.value,
}


# --- Member-tree (NODE-scoped) logins — the caller's authority over `node_id` is enforced by the
# route (org_tree.get_managed_node), so these just CRUD the assignment at the node. -------------
def _account_row(db: Session, a: UserRoleAssignment, u: User, node_name: str | None = None) -> dict:
    role = db.get(Role, a.role_id)
    return {"assignment_id": a.id, "user_id": u.id, "email": u.email, "full_name": u.full_name,
            "is_active": u.is_active, "role": role.name if role else "?", "pin_set": bool(u.pin_hash),
            "node_id": a.scope_id, "node_name": node_name or a.scope_id}


def list_node_accounts(db: Session, *, node_id: str, subtree: bool = False) -> list[dict]:
    """Web logins assigned at a node. `subtree=True` → all NODE logins anywhere in the node's subtree
    (the merchant Team view: one node-model surface for the whole scope)."""
    from app.services import org_tree
    if subtree:
        node = db.get(OrgNode, node_id)
        scope_nodes = org_tree.subtree(db, node, active_only=False) if node else []
        names = {n.id: (n.name or n.id) for n in scope_nodes}
        node_ids = list(names) or [node_id]
    else:
        n = db.get(OrgNode, node_id)
        names = {node_id: (n.name if n and n.name else node_id)}
        node_ids = [node_id]
    asgs = db.scalars(select(UserRoleAssignment).where(
        UserRoleAssignment.scope_type == ScopeType.NODE.value,
        UserRoleAssignment.scope_id.in_(node_ids),
    )).all()
    # WEB logins only — POS operators (kind="pos", synthetic @pos.local emails) are managed separately
    # (Settings → Staff & PINs); their reserved-domain emails would also fail NodeAccountOut.email (EmailStr).
    rows = [_account_row(db, a, u, names.get(a.scope_id)) for a in asgs
            if (u := db.get(User, a.user_id)) and u.kind != "pos"]
    rows.sort(key=lambda x: (x["node_name"], x["email"]))
    return rows


def create_node_account(db: Session, *, node_id: str, email: str, password: str,
                        full_name: str, role: str) -> dict:
    """Create a WEB/dashboard login (email + password) at a node. POS PINs are separate — see
    app/services/pos_staff.py."""
    if role not in NODE_GRANTABLE_ROLES:
        raise ForbiddenError("Role cannot be granted", code="role_not_allowed")
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("A user with this email already exists", code="email_taken")
    role_obj = db.scalar(select(Role).where(Role.name == role))
    if not role_obj:
        raise NotFoundError("Role not found", code="role_missing")
    user = User(email=email, full_name=full_name or email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    a = UserRoleAssignment(user_id=user.id, role_id=role_obj.id,
                           scope_type=ScopeType.NODE.value, scope_id=node_id)
    db.add(a)
    db.flush()
    node = db.get(OrgNode, node_id)
    return _account_row(db, a, user, node.name if node and node.name else None)


# --- POS staff PIN -------------------------------------------------------
def _node_merchant(db: Session, node_id: str) -> str:
    node = db.get(OrgNode, node_id)
    if node is None:
        raise NotFoundError("Node not found", code="node_not_found")
    return node.settlement_account_id


def _merchant_staff(db: Session, merchant_id: str) -> list[User]:
    """Active back-office users scoped to this merchant — via a NODE under its settlement boundary
    or a direct MERCHANT assignment. The candidate set for PIN resolution + uniqueness."""
    node_ids = select(OrgNode.id).where(OrgNode.settlement_account_id == merchant_id)
    return list(db.scalars(
        select(User).join(UserRoleAssignment, UserRoleAssignment.user_id == User.id).where(
            User.is_active.is_(True),
            or_(
                and_(UserRoleAssignment.scope_type == ScopeType.NODE.value,
                     UserRoleAssignment.scope_id.in_(node_ids)),
                and_(UserRoleAssignment.scope_type == ScopeType.MERCHANT.value,
                     UserRoleAssignment.scope_id == merchant_id),
            ),
        ).distinct()
    ).all())


def set_pin(db: Session, *, user_id: str, pin: str, merchant_id: str) -> None:
    """Set/replace a staff PIN (4–6 digits), unique within the merchant so PIN-login resolves one person."""
    if not _PIN_RE.match(pin or ""):
        raise AppError("PIN must be 4–6 digits", code="bad_pin", status_code=422)
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", code="user_not_found")
    for other in _merchant_staff(db, merchant_id):
        if other.id != user_id and other.pin_hash and verify_password(pin, other.pin_hash):
            raise ConflictError("Another staff member already uses this PIN", code="pin_taken")
    user.pin_hash = hash_password(pin)
    db.flush()


def resolve_pin(db: Session, *, merchant_id: str, pin: str) -> User | None:
    """The active staff member in this merchant whose PIN matches, else None."""
    if not _PIN_RE.match(pin or ""):
        return None
    for u in _merchant_staff(db, merchant_id):
        if u.pin_hash and verify_password(pin, u.pin_hash):
            return u
    return None


def revoke_node_account(db: Session, *, node_id: str, assignment_id: str) -> None:
    a = db.get(UserRoleAssignment, assignment_id)
    if not a or a.scope_type != ScopeType.NODE.value or a.scope_id != node_id:
        raise NotFoundError("Assignment not found", code="assignment_not_found")
    db.delete(a)
    db.flush()
