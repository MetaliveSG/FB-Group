"""POS staff (POS operators) — SEGREGATED from web/dashboard users.

A POS operator is a `User` with `kind="pos"`: a synthetic email + a locked (random, unknowable)
password so it can NEVER log into the web dashboard, and a bcrypt-hashed 6-digit **PIN** that is
unique **per storefront** (the node it's assigned at). It signs in only at `/pos` via the PIN.

We keep them as `User` rows (not a separate table) so the order/payment/audit actor graph — which
references `user_id` everywhere — keeps working unchanged. The segregation is enforced by `kind` +
the two login channels (see `auth/service.py`: `login_user` rejects `kind="pos"`; PIN-login only
considers `kind="pos"`).

PINs are stored READABLY (owner choice — see User.pin): the owner can reveal any operator's current
PIN and set a chosen one. PINs are unique per storefront. (KIV: encrypt-at-rest.)
"""
from __future__ import annotations

import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.catalog import Menu
from app.models.enums import RoleName, ScopeType
from app.models.identity import Role, User, UserRoleAssignment
from app.models.org import OrgNode

POS_KIND = "pos"
_PIN_LEN = 6
_PIN_RE = re.compile(r"^\d{4,6}$")
# The auto-provisioned starter team for a brand-new storefront: 1 manager + 2 cashiers.
_DEFAULT_TEAM = [
    (RoleName.MANAGER.value, "Manager"),
    (RoleName.CASHIER.value, "Cashier 1"),
    (RoleName.CASHIER.value, "Cashier 2"),
]


# --- node / lookup helpers ------------------------------------------------
def node_for_outlet(db: Session, outlet_id: str) -> OrgNode | None:
    """The storefront node backing an outlet (menu.id == node.id, menu.outlet_id == outlet)."""
    node_id = db.scalar(select(Menu.id).where(Menu.outlet_id == outlet_id))
    return db.get(OrgNode, node_id) if node_id else None


def _pos_users_at_node(db: Session, node_id: str, *, active_only: bool = True) -> list[User]:
    stmt = (
        select(User)
        .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
        .where(
            User.kind == POS_KIND,
            UserRoleAssignment.scope_type == ScopeType.NODE.value,
            UserRoleAssignment.scope_id == node_id,
        )
    )
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    return list(db.scalars(stmt.distinct()).all())


def _assignment_at(db: Session, *, user_id: str, node_id: str) -> UserRoleAssignment | None:
    return db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.scope_type == ScopeType.NODE.value,
            UserRoleAssignment.scope_id == node_id,
        )
    )


# --- PIN generation (unique per storefront) -------------------------------
def _random_pin() -> str:
    return f"{secrets.randbelow(10 ** _PIN_LEN):0{_PIN_LEN}d}"


def _pin_unique_at_node(db: Session, node_id: str, pin: str, *, exclude_user_id: str | None = None) -> bool:
    for u in _pos_users_at_node(db, node_id):
        if u.id != exclude_user_id and u.pin and u.pin == pin:
            return False
    return True


def _fresh_pin_for_node(db: Session, node_id: str, *, exclude_user_id: str | None = None) -> str:
    for _ in range(50):
        pin = _random_pin()
        if _pin_unique_at_node(db, node_id, pin, exclude_user_id=exclude_user_id):
            return pin
    raise ConflictError("Could not allocate a unique PIN for this storefront", code="pin_exhausted")


def reset_pin(db: Session, *, user_id: str, node_id: str, pin: str | None = None) -> dict:
    """Set a POS user's PIN — a chosen `pin` (validated, must be unique at the storefront) or, if None,
    a fresh server-generated one. Returns the row incl. the (readable) PIN."""
    user = db.get(User, user_id)
    if user is None or user.kind != POS_KIND or _assignment_at(db, user_id=user_id, node_id=node_id) is None:
        raise NotFoundError("POS user not found at this storefront", code="pos_user_not_found")
    if pin is not None:
        if not _PIN_RE.match(pin):
            raise AppError("PIN must be 4–6 digits", code="bad_pin", status_code=422)
        if not _pin_unique_at_node(db, node_id, pin, exclude_user_id=user_id):
            raise ConflictError("Another operator at this storefront already uses that PIN", code="pin_taken")
    else:
        pin = _fresh_pin_for_node(db, node_id, exclude_user_id=user_id)
    user.pin = pin
    db.flush()
    return {**_row(db, user, node_id), "pin": pin}


# --- create / list / delete ----------------------------------------------
def _synthetic_email(db: Session, node_id: str) -> str:
    for _ in range(50):
        email = f"pos-{node_id[:8]}-{secrets.token_hex(3)}@pos.local"
        if not db.scalar(select(User.id).where(User.email == email)):
            return email
    raise ConflictError("Could not allocate a POS account id", code="pos_email_exhausted")


def create_pos_user(db: Session, *, node_id: str, full_name: str, role: str, pin: str | None = None) -> dict:
    """Create a kind='pos' operator at a storefront node with a PIN — a chosen one (validated/unique)
    or a fresh server-generated one. Returns the row incl. the (readable) PIN."""
    if role not in {RoleName.MANAGER.value, RoleName.CASHIER.value, RoleName.STAFF.value, RoleName.FINANCE.value}:
        raise ConflictError("Role cannot be granted", code="role_not_allowed")
    role_obj = db.scalar(select(Role).where(Role.name == role))
    if role_obj is None:
        raise NotFoundError("Role not found", code="role_missing")
    if pin is not None:
        if not _PIN_RE.match(pin):
            raise AppError("PIN must be 4–6 digits", code="bad_pin", status_code=422)
        if not _pin_unique_at_node(db, node_id, pin):
            raise ConflictError("Another operator at this storefront already uses that PIN", code="pin_taken")
    else:
        pin = _fresh_pin_for_node(db, node_id)
    user = User(
        email=_synthetic_email(db, node_id),
        full_name=full_name or role.capitalize(),
        password_hash=hash_password(secrets.token_urlsafe(32)),  # locked — unknowable, never used
        kind=POS_KIND,
        pin=pin,
    )
    db.add(user)
    db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role_obj.id,
                              scope_type=ScopeType.NODE.value, scope_id=node_id))
    db.flush()
    return {**_row(db, user, node_id), "pin": pin}


def provision_team(db: Session, node: OrgNode) -> list[dict]:
    """Idempotently seed a storefront's starter POS team (1 manager + 4 cashiers). No-op if any POS
    user already exists at the node. Returns [{full_name, role, pin}, ...] for show-once (empty if skipped)."""
    if not node.sells:
        return []
    if _pos_users_at_node(db, node.id, active_only=False):
        return []
    return [create_pos_user(db, node_id=node.id, full_name=name, role=role) for role, name in _DEFAULT_TEAM]


def list_pos_users(db: Session, *, node_id: str) -> list[dict]:
    rows = [_row(db, u, node_id) for u in _pos_users_at_node(db, node_id, active_only=False)]
    rows.sort(key=lambda r: (r["role"] != "manager", r["full_name"]))
    return rows


def delete_pos_user(db: Session, *, node_id: str, user_id: str) -> None:
    a = _assignment_at(db, user_id=user_id, node_id=node_id)
    user = db.get(User, user_id)
    if a is None or user is None or user.kind != POS_KIND:
        raise NotFoundError("POS user not found at this storefront", code="pos_user_not_found")
    db.delete(a)
    db.delete(user)   # POS users are single-node; safe to hard-delete with their assignment
    db.flush()


def _row(db: Session, user: User, node_id: str) -> dict:
    a = _assignment_at(db, user_id=user.id, node_id=node_id)
    role = db.get(Role, a.role_id) if a else None
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "role": role.name if role else "?",
        "is_active": user.is_active,
        "pin": user.pin,                 # readable — the owner reveals it via the eye
        "pin_set": bool(user.pin),
    }


# --- PIN login resolution (per storefront) --------------------------------
def resolve_pos_pin(db: Session, *, node_id: str, pin: str) -> User | None:
    """The active POS operator at this storefront whose PIN matches, else None."""
    if not _PIN_RE.match(pin or ""):
        return None
    for u in _pos_users_at_node(db, node_id):
        if u.pin and u.pin == pin:
            return u
    return None


# --- backfill -------------------------------------------------------------
def provision_teams_missing(db: Session) -> dict:
    """Seed a starter POS team for every sellable node that has none yet. Idempotent."""
    nodes = list(db.scalars(select(OrgNode).where(OrgNode.sells.is_(True))).all())
    seeded = 0
    for node in nodes:
        if provision_team(db, node):
            seeded += 1
    return {"storefronts_seeded": seeded}
