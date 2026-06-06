"""Demo merchants — idempotent ensure-script for the two UI-onboarded groups + their logins.

Captures the LIVE member-tree (Breadtalk Group + Pepper Lunch Group) so it survives a data wipe:
"re-run → live reflects it" (the `seed_kampong` convention). Node ids are FIXED to the values the
UI minted, so a fresh rebuild reproduces the SAME ids → the SAME QR tokens (`provision_missing`
derives the token from node name+id) → the hardcoded customer links on the landing page stay valid.

Idempotent + ADDITIVE: upserts nodes by id (a no-op on the live DB, since the values match), backfills
each storefront's Outlet+Menu+QR, ensures the three Manager logins (create-if-absent, else reset the
password + reconcile the node role). It does NOT prune other users/nodes — safe on a live demo DB.

Run:  cd apps/api && .venv/bin/python -m app.seed_demo_merchants
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.enums import RoleName, ScopeType
from app.models.identity import User, UserRoleAssignment
from app.models.org import PATH_SEP, OrgNode
from app.models.tenancy import Merchant
from app.services import storefronts

PW = "Password123!"
CHAIN, STOREFRONT = "CHAIN", "STOREFRONT"

# Stable node ids = the ones the UI minted (so QR tokens are reproducible across a fresh rebuild).
BREADTALK_GROUP = "69443c4a845645409164115466079fd6"
TOAST_BOX = "2b6d04fb3c654df08aec35923c0d3b74"
BREADTALK_BAKERY = "1d3b5ac7170648ddbede6caa5ee65382"
TOASTBOX_ORCHARD = "f1878dd302e84bdaaa1eb8a1a3370ce4"
TOASTBOX_TAKA = "ac3c6bedd35c4cafbb344c276bea777a"
PEPPER_GROUP = "9a05bb10711a47bbb1712302b23a33a5"
PEPPER_AMK = "97c2695a8ec94714ac5c87c46008b870"
PEPPER_TPY = "0ab5b283369b421e8a1e90d5f0b06164"
PEPPER_SBW = "62b01dd9dab74468ac44d27d963836e3"
PEPPER_SUB_GROUP = "6d4ebac88d0d4c1b9883940f269d2877"
PEPPER_SUB_YIS = "bd0463d5b3f5489684777c197b805e79"

# (id, parent_id, kind, label) — parent-before-child so path/depth derive in one pass.
NODES = [
    (BREADTALK_GROUP, None, CHAIN, "Breadtalk Group"),
    (TOAST_BOX, BREADTALK_GROUP, CHAIN, "Toast Box"),
    (BREADTALK_BAKERY, BREADTALK_GROUP, CHAIN, "Breadtalk Bakery"),
    (TOASTBOX_ORCHARD, TOAST_BOX, STOREFRONT, "Toast Box @ Orchard"),
    (TOASTBOX_TAKA, TOAST_BOX, STOREFRONT, "Toast Box @ Taka"),
    (PEPPER_GROUP, None, CHAIN, "Pepper Lunch Group"),
    (PEPPER_AMK, PEPPER_GROUP, STOREFRONT, "Pepper Lunch @ AMK"),
    (PEPPER_TPY, PEPPER_GROUP, STOREFRONT, "Pepper Lunch @ TPY"),
    (PEPPER_SBW, PEPPER_GROUP, STOREFRONT, "Pepper Lunch @ SBW"),
    (PEPPER_SUB_GROUP, PEPPER_GROUP, CHAIN, "Pepper Lunch Sub Group"),
    (PEPPER_SUB_YIS, PEPPER_SUB_GROUP, STOREFRONT, "Pepper Lunch Sub @ YIS"),
]

# Each group is its own tenant (settlement boundary) AND its own loyalty ring.
SETTLEMENT_BOUNDARIES = {BREADTALK_GROUP, PEPPER_GROUP}
LOYALTY_DOMAINS = {BREADTALK_GROUP, PEPPER_GROUP}

# (email, full_name, node_id) — owner-equivalent Manager at each scope.
ACCOUNTS = [
    ("owner@breadtalk.sg", "Breadtalk Owner", BREADTALK_GROUP),
    ("owner@pepperlunch.sg", "Pepper Lunch Owner", PEPPER_GROUP),
    ("manager@toastbox.sg", "Toast Box Orchard Manager", TOASTBOX_ORCHARD),
]


def build_demo_merchants(db: Session) -> dict:
    """Idempotently ensure the two demo groups, their storefronts (provisioned), and the three
    Manager logins. Safe to re-run; additive (no pruning of other data). Returns a summary."""
    roles = seed_rbac(db)
    label_by_id = {nid: label for nid, _p, _k, label in NODES}

    # Typed Merchant row per tenant boundary (id == org-node id, per the spine contract) so each
    # group shows in the operator directory and resolves as a merchant.
    for tid in SETTLEMENT_BOUNDARIES:
        if db.get(Merchant, tid) is None:
            db.add(Merchant(id=tid, name=label_by_id[tid], legal_name=label_by_id[tid],
                            country="SG", is_active=True))
    db.flush()

    # path/depth + nearest-ancestor boundary/loyalty resolution, parent-before-child.
    info: dict[str, tuple[str, int, str, str]] = {}
    for nid, pid, kind, label in NODES:
        if pid is None:
            path, depth, settle, loyalty = nid, 0, nid, nid
        else:
            ppath, pdepth, psettle, ployalty = info[pid]
            path, depth = PATH_SEP.join([ppath, nid]), pdepth + 1
            settle = nid if nid in SETTLEMENT_BOUNDARIES else psettle
            loyalty = nid if nid in LOYALTY_DOMAINS else ployalty
        info[nid] = (path, depth, settle, loyalty)

        node = db.get(OrgNode, nid) or OrgNode(id=nid)
        node.parent_id = pid
        node.role = kind
        node.name = label
        node.depth = depth
        node.path = path
        node.sells = kind == STOREFRONT
        node.chain_stopped = False
        node.is_settlement_boundary = nid in SETTLEMENT_BOUNDARIES
        node.is_loyalty_domain = nid in LOYALTY_DOMAINS
        node.settlement_account_id = settle
        node.loyalty_domain_id = loyalty
        node.is_active = True
        db.add(node)
    db.flush()

    # Mint each storefront's typed Outlet + Menu(id==node.id) + DiningTable + stable QRCode.
    storefronts.provision_missing(db)

    # Ensure the three Manager logins (create-if-absent, else reset pw + reconcile the node role).
    for email, name, node_id in ACCOUNTS:
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            u = User(email=email, full_name=name, password_hash=hash_password(PW))
            db.add(u)
            db.flush()
        else:
            u.password_hash = hash_password(PW)   # re-run restores the known demo password
            u.is_active = True
        # Reconcile NODE-scope assignments only (leave any merchant-scope owner role intact).
        for a in db.scalars(select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == u.id,
            UserRoleAssignment.scope_type == ScopeType.NODE.value,
        )).all():
            db.delete(a)
        db.flush()
        db.add(UserRoleAssignment(user_id=u.id, role_id=roles[RoleName.MANAGER.value].id,
                                  scope_type=ScopeType.NODE.value, scope_id=node_id))
    db.flush()

    # Every storefront gets a starter POS team (1 manager + 4 cashiers) so the till works out of the
    # box. Idempotent (skips storefronts that already have POS staff). PINs are random — the owner
    # reveals one via Settings → Staff & PINs → Reset PIN (they're hashed, never reproducible).
    from app.services import pos_staff
    pos = pos_staff.provision_teams_missing(db)
    db.commit()
    return {
        "nodes": len(NODES),
        "storefronts": sum(1 for _n, _p, k, _l in NODES if k == STOREFRONT),
        "tenants": len(SETTLEMENT_BOUNDARIES),
        "accounts": len(ACCOUNTS),
        "pos_teams_seeded": pos["storefronts_seeded"],
    }


if __name__ == "__main__":  # `python -m app.seed_demo_merchants` against the configured DB
    from app.db.session import SessionLocal
    with SessionLocal() as _db:
        print(build_demo_merchants(_db))
