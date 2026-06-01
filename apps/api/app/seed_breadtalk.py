"""BreadTalk Group — a real-shape **Enterprise** org tree, used to PROVE the unlimited
member-tree + node-scoped RBAC cascade.

Shape (depth 0→4, deeper than the typed chain's 3; an Enterprise spanning TWO merchants):

    Enterprise: BreadTalk Group                 (btg, depth 0)
     ├ Merchant: BreadTalk (F&B) Pte Ltd        (m1)
     │  ├ Brand: BreadTalk (bakery)             → Outlets ION, VivoCity → Stall each
     │  ├ Brand: Toast Box                      → Outlet Tampines → Stall
     │  └ Brand: Food Republic (foodcourt)      → Outlet VivoCity → Stalls ×3
     └ Merchant: Din Tai Fung SG Pte Ltd        (m2)
        └ Brand: Din Tai Fung                   → Outlet Paragon → Stall

Builds pure `org_nodes` (the member-tree spine) + staff accounts at every tier with **NODE-scoped**
role assignments, so authority cascades DOWN each node's subtree. Idempotent (upsert by stable id).
Not wired into build_demo — call `build_breadtalk(db)`; used by the proof test + a live demo.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.enums import RoleName, ScopeType
from app.models.identity import User, UserRoleAssignment
from app.models.org import PATH_SEP, OrgNode

PW = "Password123!"

# (id, parent_id, role, label) — parent-before-child so paths/depths derive in one pass.
NODES = [
    ("btg", None, "ENTERPRISE", "BreadTalk Group"),
    ("m1", "btg", "MERCHANT", "BreadTalk (F&B) Pte Ltd"),
    ("m2", "btg", "MERCHANT", "Din Tai Fung SG Pte Ltd"),
    ("b_bt", "m1", "BRAND", "BreadTalk (bakery)"),
    ("b_tb", "m1", "BRAND", "Toast Box"),
    ("b_fr", "m1", "BRAND", "Food Republic"),
    ("b_dtf", "m2", "BRAND", "Din Tai Fung"),
    ("o_bt_ion", "b_bt", "OUTLET", "BreadTalk @ ION"),
    ("o_bt_vivo", "b_bt", "OUTLET", "BreadTalk @ VivoCity"),
    ("o_tb_tamp", "b_tb", "OUTLET", "Toast Box @ Tampines"),
    ("o_fr_vivo", "b_fr", "OUTLET", "Food Republic @ VivoCity"),
    ("o_dtf_para", "b_dtf", "OUTLET", "Din Tai Fung @ Paragon"),
    ("s_bt_ion", "o_bt_ion", "STALL", "BreadTalk counter (ION)"),
    ("s_bt_vivo", "o_bt_vivo", "STALL", "BreadTalk counter (VivoCity)"),
    ("s_tb_tamp", "o_tb_tamp", "STALL", "Toast Box counter (Tampines)"),
    ("s_fr_chic", "o_fr_vivo", "STALL", "Chicken Rice (Food Republic)"),
    ("s_fr_laksa", "o_fr_vivo", "STALL", "Laksa (Food Republic)"),
    ("s_fr_west", "o_fr_vivo", "STALL", "Western (Food Republic)"),
    ("s_dtf_para", "o_dtf_para", "STALL", "Din Tai Fung kitchen (Paragon)"),
]

# (email, full_name, role, node_id) — the entire company, top (Enterprise) → bottom (Stall).
ACCOUNTS = [
    ("ceo@breadtalk.sg", "Group CEO", RoleName.GROUP_CEO.value, "btg"),
    ("coo@breadtalk.sg", "Group COO", RoleName.GROUP_COO.value, "btg"),
    ("cfo@breadtalk.sg", "Group CFO", RoleName.GROUP_CFO.value, "btg"),
    ("accountant@breadtalk.sg", "Group Accountant", RoleName.GROUP_ACCOUNTANT.value, "btg"),
    ("owner.m1@breadtalk.sg", "BreadTalk Pte Ltd Owner", RoleName.MERCHANT_OWNER.value, "m1"),
    ("bm.toastbox@breadtalk.sg", "Toast Box Brand Manager", RoleName.BRAND_MANAGER.value, "b_tb"),
    ("am.foodrepublic@breadtalk.sg", "Food Republic Area Manager", RoleName.AREA_MANAGER.value, "b_fr"),
    ("om.ion@breadtalk.sg", "BreadTalk ION Outlet Manager", RoleName.OUTLET_MANAGER.value, "o_bt_ion"),
    ("stall.chicken@breadtalk.sg", "Chicken Rice Stall Operator", RoleName.STALL_OPERATOR.value, "s_fr_chic"),
    ("cashier.tampines@breadtalk.sg", "Toast Box Tampines Cashier", RoleName.STAFF.value, "o_tb_tamp"),
    ("bm.dtf@breadtalk.sg", "Din Tai Fung Brand Manager", RoleName.BRAND_MANAGER.value, "b_dtf"),
]


def build_breadtalk(db: Session) -> dict:
    """Idempotently build the BreadTalk member-tree + accounts. Returns a small summary."""
    roles = seed_rbac(db)
    info: dict[str, tuple[str, int, str]] = {}  # id -> (path, depth, loyalty_domain)
    for nid, pid, role, _label in NODES:
        if pid is None:
            path, depth, domain = nid, 0, nid
        else:
            ppath, pdepth, pdomain = info[pid]
            path, depth = PATH_SEP.join([ppath, nid]), pdepth + 1
            domain = nid if role == "MERCHANT" else pdomain
        info[nid] = (path, depth, domain)
        node = db.get(OrgNode, nid) or OrgNode(id=nid)
        node.parent_id = pid
        node.role = role
        node.depth = depth
        node.path = path
        node.sells = role == "STALL"
        node.is_settlement_boundary = role == "MERCHANT"
        node.is_loyalty_domain = role == "MERCHANT"
        node.loyalty_domain_id = domain
        node.settlement_account_id = domain
        node.is_active = True
        db.add(node)
    db.flush()

    for email, name, role, node_id in ACCOUNTS:
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            u = User(email=email, full_name=name, password_hash=hash_password(PW))
            db.add(u)
            db.flush()
        exists = db.scalar(select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == u.id,
            UserRoleAssignment.scope_type == ScopeType.NODE.value,
            UserRoleAssignment.scope_id == node_id,
        ))
        if exists is None:
            db.add(UserRoleAssignment(user_id=u.id, role_id=roles[role].id,
                                      scope_type=ScopeType.NODE.value, scope_id=node_id))
    db.commit()
    return {
        "nodes": len(NODES),
        "accounts": len(ACCOUNTS),
        "max_depth": max(d for _p, d, _dom in info.values()),
        "merchants": sum(1 for _n, _p, r, _l in NODES if r == "MERCHANT"),
    }


if __name__ == "__main__":  # `python -m app.seed_breadtalk` against the configured DB
    from app.db.session import SessionLocal
    with SessionLocal() as _db:
        print(build_breadtalk(_db))
