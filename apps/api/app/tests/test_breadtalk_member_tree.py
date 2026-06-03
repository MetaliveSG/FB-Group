"""PROOF: the unlimited member-tree + node-scoped RBAC cascade, using BreadTalk Group.

The member tree is Chain (structural) + Storefront (sells, leaf). Two Chains are tenants
(settlement boundaries); the top Chain is the loyalty domain. Authority = tree position: a Manager
high on a Chain commands its whole branch; Cashier/Staff sit at a Storefront; Finance is read-only.
Asserts: the spine holds arbitrary depth; authority cascades DOWN a subtree; a node sees neither
siblings nor upline; only a Chain can grow, only a Storefront sells.
"""
from sqlalchemy import select

from app.auth.access import ALL_OUTLETS, resolve_scope
from app.models.identity import User
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.services import org_tree
from app.tests.helpers import staff_token


def _scope(db, email):
    return resolve_scope(db, db.scalar(select(User).where(User.email == email)))


def _auth(client, email):
    return {"Authorization": f"Bearer {staff_token(client, email)}"}


def test_tree_is_deep_and_complete(client, db):
    res = build_breadtalk(db)
    assert res["nodes"] == 24 and res["accounts"] == 13
    assert res["storefronts"] == 12 and res["tenants"] == 5 and res["leases"] == 3
    # Depth 4 = Chain(0)→Chain(1)→Chain(2)→Chain(3, foodcourt)→Storefront(4) — deeper than a fixed chain.
    assert res["max_depth"] == 4
    btg = db.get(OrgNode, "btg")
    # The group's OWN sellable stalls = 7 brand storefronts + 2 BT-coffeeshop house stalls = 9.
    # Leased-in independent stalls (Lim's/Ah Huat/Mr Bean) are own roots → NOT under btg.
    assert len(org_tree.sellable_under(db, btg)) == 9
    assert len(org_tree.sellable_under(db, db.get(OrgNode, "b_fr"))) == 3   # Food Republic's 3 house stalls
    # Only Storefronts sell; the foodcourt location is a (stopped) Chain.
    assert db.get(OrgNode, "o_bt_ion").sells and not db.get(OrgNode, "o_fr_vivo").sells
    assert db.get(OrgNode, "o_fr_vivo").chain_stopped is True


def test_manager_at_top_commands_whole_group(client, db):
    build_breadtalk(db)
    s = _scope(db, "ceo@breadtalk.sg")                            # Manager @ the group Chain
    # Full command of BOTH owned tenants + read-only turnover on t_mb (a GTO tenant leasing into the
    # group's Food Republic foodcourt — the landlord reads its turnover to bill the %).
    assert s.accessible_merchant_ids == {"m1", "m2", "t_mb"}
    assert s.outlet_limit("m1") is ALL_OUTLETS and s.outlet_limit("m2") is ALL_OUTLETS
    assert s.can("org.manage", "m1") and s.can("report.view", "m2")
    assert s.can("report.view", "t_mb") and not s.can("org.manage", "t_mb")   # turnover read only


def test_finance_is_read_only_group_wide(client, db):
    build_breadtalk(db)
    s = _scope(db, "cfo@breadtalk.sg")                            # Finance @ the group Chain
    assert s.accessible_merchant_ids == {"m1", "m2", "t_mb"}      # +t_mb turnover (GTO foodcourt tenant)
    assert s.can("report.view", "m1") and s.can("audit.view", "m2")
    assert not s.can("order.manage", "m1") and not s.can("org.manage", "m1")   # read-only


def test_chain_manager_isolated_to_its_branch(client, db):
    build_breadtalk(db)
    s = _scope(db, "mgr.toastbox@breadtalk.sg")                  # Manager @ Toast Box Chain (under m1)
    assert s.accessible_merchant_ids == {"m1"}                   # only its tenant
    assert s.outlet_limit("m1") == {"o_tb_tamp"}                 # only Toast Box's storefront
    assert not s.can_view_outlet("m1", "o_bt_ion")              # sibling chain's storefront — hidden
    assert "m2" not in s.accessible_merchant_ids                # other tenant — hidden


def test_storefront_and_foodcourt_scoping(client, db):
    build_breadtalk(db)
    fr = _scope(db, "mgr.foodrepublic@breadtalk.sg")            # Manager @ Food Republic Chain
    assert fr.outlet_limit("m1") == {"s_fr_chic", "s_fr_laksa", "s_fr_west"}   # its 3 storefronts
    sm = _scope(db, "mgr.ion@breadtalk.sg")                     # Manager @ a single Storefront
    assert sm.outlet_limit("m1") == {"o_bt_ion"}
    staff = _scope(db, "staff.chicken@breadtalk.sg")           # Staff @ one Storefront
    assert staff.outlet_limit("m1") == {"s_fr_chic"}
    assert staff.can("payment.process", "m1") and not staff.can("org.manage", "m1")


def test_cross_tenant_isolation(client, db):
    build_breadtalk(db)
    dtf = _scope(db, "mgr.dtf@breadtalk.sg")                    # Manager @ Din Tai Fung (under m2)
    assert dtf.accessible_merchant_ids == {"m2"}
    assert "m1" not in dtf.accessible_merchant_ids             # cannot see BreadTalk's tenant


def test_every_tier_account_can_log_in(client, db):
    build_breadtalk(db)
    for email in ["ceo@breadtalk.sg", "cfo@breadtalk.sg", "mgr.toastbox@breadtalk.sg",
                  "mgr.ion@breadtalk.sg", "cashier.ion@breadtalk.sg", "staff.chicken@breadtalk.sg",
                  "mgr.dtf@breadtalk.sg"]:
        assert staff_token(client, email)


# --- Org-tree endpoints: visibility + the Chain/Storefront create rules ------
def test_tree_endpoint_scopes_to_downline(client, db):
    build_breadtalk(db)
    ceo = client.get("/api/v1/org/tree", headers=_auth(client, "ceo@breadtalk.sg"))
    # Whole group subtree = 18 (15 brand nodes + the BT Coffeeshop venue & its 2 house stalls).
    # The independent leased tenants are own roots → not in the group's subtree.
    assert ceo.status_code == 200 and len(ceo.json()["nodes"]) == 18
    assert ceo.json()["can_manage"] is True

    bm = client.get("/api/v1/org/tree", headers=_auth(client, "mgr.toastbox@breadtalk.sg"))
    bm_ids = {n["id"] for n in bm.json()["nodes"]}
    assert bm_ids == {"b_tb", "o_tb_tamp"}                                # its Chain + Storefront only
    assert "b_bt" not in bm_ids and "m2" not in bm_ids                    # sibling + other tenant hidden


def test_create_rules_chain_and_storefront(client, db):
    build_breadtalk(db)
    tb = _auth(client, "mgr.toastbox@breadtalk.sg")
    # A Chain may grow a Storefront or a Chain.
    sf = client.post("/api/v1/org/nodes", headers=tb,
                     json={"parent_id": "b_tb", "role": "STOREFRONT", "name": "Toast Box @ Jurong"})
    assert sf.status_code == 201 and sf.json()["sells"] is True
    ch = client.post("/api/v1/org/nodes", headers=tb,
                     json={"parent_id": "b_tb", "role": "CHAIN", "name": "Toast Box West Region"})
    assert ch.status_code == 201 and ch.json()["sells"] is False
    # A Storefront is a hard leaf — nothing attaches under it.
    assert client.post("/api/v1/org/nodes", headers=tb,
                       json={"parent_id": "o_tb_tamp", "role": "STOREFRONT", "name": "x"}).status_code == 400


def test_stop_chain_forces_storefronts_only(client, db):
    build_breadtalk(db)
    fr = _auth(client, "mgr.foodrepublic@breadtalk.sg")          # manages the foodcourt Chain
    # o_fr_vivo is chain_stopped → a Storefront is allowed, a sub-Chain is rejected.
    ok = client.post("/api/v1/org/nodes", headers=fr,
                     json={"parent_id": "o_fr_vivo", "role": "STOREFRONT", "name": "Nasi Padang"})
    assert ok.status_code == 201
    bad = client.post("/api/v1/org/nodes", headers=fr,
                      json={"parent_id": "o_fr_vivo", "role": "CHAIN", "name": "x"})
    assert bad.status_code == 400


def test_per_node_subscription_fee(client, db):
    build_breadtalk(db)
    ceo = _auth(client, "ceo@breadtalk.sg")
    # Create a storefront with its own fee, then a sibling with a different fee (more or less).
    a = client.post("/api/v1/org/nodes", headers=ceo,
                    json={"parent_id": "b_tb", "role": "STOREFRONT", "name": "Kiosk A",
                          "subscription_fee": "49.90"})
    assert a.status_code == 201 and str(a.json()["subscription_fee"]) in ("49.90", "49.9")
    # Update a node's fee independently.
    upd = client.patch(f"/api/v1/org/nodes/{a.json()['id']}", headers=ceo,
                       json={"subscription_fee": "9.90"})
    assert upd.status_code == 200 and str(upd.json()["subscription_fee"]) in ("9.90", "9.9")


def test_finance_cannot_build_tree(client, db):
    build_breadtalk(db)
    cfo = _auth(client, "cfo@breadtalk.sg")
    assert client.get("/api/v1/org/tree", headers=cfo).json()["can_manage"] is False
    assert client.post("/api/v1/org/nodes", headers=cfo,
                       json={"parent_id": "btg", "role": "CHAIN", "name": "x"}).status_code == 403


def test_rename_node_and_status_mirrors_tenant(client, db):
    build_breadtalk(db)
    ceo = _auth(client, "ceo@breadtalk.sg")
    # Rename a pure-spine node (the gap the user hit).
    r = client.patch("/api/v1/org/nodes/btg", headers=ceo, json={"name": "BreadTalk Holdings"})
    assert r.status_code == 200 and r.json()["name"] == "BreadTalk Holdings"
    # Suspending a TENANT node mirrors onto its typed Merchant (single status, not two flags).
    from app.models.tenancy import Merchant
    client.patch("/api/v1/org/nodes/m1", headers=ceo, json={"is_active": False})
    assert db.get(Merchant, "m1").is_active is False
    client.patch("/api/v1/org/nodes/m1", headers=ceo, json={"is_active": True})
    assert db.get(Merchant, "m1").is_active is True


def test_node_accounts_crud_and_scoping(client, db):
    build_breadtalk(db)
    ceo = _auth(client, "ceo@breadtalk.sg")
    # List existing logins at a storefront (seeded mgr + cashier).
    got = client.get("/api/v1/org/nodes/o_bt_ion/accounts", headers=ceo)
    assert got.status_code == 200 and {a["email"] for a in got.json()} >= {"mgr.ion@breadtalk.sg", "cashier.ion@breadtalk.sg"}
    # Add a new Staff login at a storefront.
    created = client.post("/api/v1/org/nodes/o_bt_ion/accounts", headers=ceo,
                          json={"email": "new.staff@breadtalk.sg", "password": "Password123!",
                                "full_name": "New Staff", "role": "staff"})
    assert created.status_code == 201 and created.json()["role"] == "staff"
    aid = created.json()["assignment_id"]
    # The new login can authenticate and is scoped to that one storefront.
    assert staff_token(client, "new.staff@breadtalk.sg")
    s = _scope(db, "new.staff@breadtalk.sg")
    assert s.outlet_limit("m1") == {"o_bt_ion"}
    # Revoke it.
    assert client.delete(f"/api/v1/org/nodes/o_bt_ion/accounts/{aid}", headers=ceo).status_code == 204
    assert "new.staff@breadtalk.sg" not in {a["email"] for a in client.get("/api/v1/org/nodes/o_bt_ion/accounts", headers=ceo).json()}


def test_node_accounts_require_manage_rights(client, db):
    build_breadtalk(db)
    # The Toast Box manager can manage logins at its own storefront, but NOT at a sibling's.
    tb = _auth(client, "mgr.toastbox@breadtalk.sg")
    assert client.get("/api/v1/org/nodes/o_tb_tamp/accounts", headers=tb).status_code == 200
    assert client.get("/api/v1/org/nodes/o_bt_ion/accounts", headers=tb).status_code == 403
    # Finance (read-only, no org.manage) cannot add a login anywhere.
    cfo = _auth(client, "cfo@breadtalk.sg")
    assert client.post("/api/v1/org/nodes/o_bt_ion/accounts", headers=cfo,
                       json={"email": "x@y.sg", "password": "Password123!", "role": "staff"}).status_code == 403
