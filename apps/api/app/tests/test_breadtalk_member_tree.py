"""PROOF: the unlimited member-tree + node-scoped RBAC cascade, using BreadTalk Group.

Builds the full Enterprise→Merchant→Brand→Outlet→Stall tree (depth 0–4, two merchants under one
group) with accounts at every tier, then proves: the spine holds arbitrary depth; authority
assigned at a node cascades DOWN its subtree; and a node can see neither siblings nor upline.
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


def test_tree_is_deep_and_complete(client, db):
    res = build_breadtalk(db)
    assert res["nodes"] == 19 and res["accounts"] == 11 and res["merchants"] == 2
    # Depth 4 = Enterprise(0)→Merchant(1)→Brand(2)→Outlet(3)→Stall(4) — deeper than the typed chain's 3.
    assert res["max_depth"] == 4
    # Spine cascade (path-prefix, no recursion): every sellable storefront under the Enterprise.
    ent = db.get(OrgNode, "btg")
    assert len(org_tree.sellable_under(db, ent)) == 7          # all 7 stalls, both merchants
    assert len(org_tree.sellable_under(db, db.get(OrgNode, "b_fr"))) == 3   # Food Republic's 3 stalls
    assert len(org_tree.outlet_ids_under(db, ent)) == 5        # all 5 outlets


def test_ceo_sees_whole_group(client, db):
    build_breadtalk(db)
    s = _scope(db, "ceo@breadtalk.sg")
    assert s.accessible_merchant_ids == {"m1", "m2"}          # Enterprise spans BOTH merchants
    assert s.outlet_limit("m1") is ALL_OUTLETS and s.outlet_limit("m2") is ALL_OUTLETS
    assert s.can("merchant.manage", "m1") and s.can("report.view", "m2")


def test_cfo_is_finance_read_only_group_wide(client, db):
    build_breadtalk(db)
    s = _scope(db, "cfo@breadtalk.sg")
    assert s.accessible_merchant_ids == {"m1", "m2"}          # whole group
    assert s.can("report.view", "m1") and s.can("audit.view", "m2")
    assert not s.can("order.manage", "m1") and not s.can("merchant.manage", "m1")  # read-only finance


def test_brand_manager_isolated_to_its_brand(client, db):
    build_breadtalk(db)
    s = _scope(db, "bm.toastbox@breadtalk.sg")               # Brand Manager @ Toast Box (under m1)
    assert s.accessible_merchant_ids == {"m1"}               # only its merchant
    assert s.outlet_limit("m1") == {"o_tb_tamp"}             # only Toast Box's outlet
    assert s.can_view_outlet("m1", "o_tb_tamp")
    assert not s.can_view_outlet("m1", "o_bt_ion")          # sibling brand (BreadTalk bakery) — hidden
    assert "m2" not in s.accessible_merchant_ids             # other merchant (Din Tai Fung) — hidden
    assert not s.can("merchant.manage", "m1")               # upline (merchant-level) — denied


def test_area_outlet_stall_scoping(client, db):
    build_breadtalk(db)
    am = _scope(db, "am.foodrepublic@breadtalk.sg")          # Area Manager @ Food Republic brand
    assert am.outlet_limit("m1") == {"o_fr_vivo"}            # the brand's outlet(s)
    om = _scope(db, "om.ion@breadtalk.sg")                   # Outlet Manager @ ION
    assert om.outlet_limit("m1") == {"o_bt_ion"}
    stall = _scope(db, "stall.chicken@breadtalk.sg")         # Stall Operator @ Chicken Rice
    assert stall.outlet_limit("m1") == {"o_fr_vivo"}        # scopes to the stall's parent outlet
    assert stall.can("payment.process", "m1") and not stall.can("outlet.manage", "m1")


def test_cross_merchant_isolation_within_enterprise(client, db):
    build_breadtalk(db)
    dtf = _scope(db, "bm.dtf@breadtalk.sg")                  # Brand Manager @ Din Tai Fung (under m2)
    assert dtf.accessible_merchant_ids == {"m2"}
    assert "m1" not in dtf.accessible_merchant_ids           # cannot see BreadTalk's merchant at all


def test_every_tier_account_can_log_in(client, db):
    build_breadtalk(db)
    for email in ["ceo@breadtalk.sg", "cfo@breadtalk.sg", "bm.toastbox@breadtalk.sg",
                  "om.ion@breadtalk.sg", "stall.chicken@breadtalk.sg", "bm.dtf@breadtalk.sg"]:
        assert staff_token(client, email)   # staff_token asserts a 200 login
