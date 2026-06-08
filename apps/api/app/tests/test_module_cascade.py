"""Phase A1 — per-node module flags resolve via the org-tree cascade (nearest explicit ancestor wins,
NULL = inherit, fallback to Merchant.settings)."""
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.services import boundaries
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer


def _attach_node(db, w, **flags):
    """Give a make_world outlet a storefront OrgNode (id == menu.id) so per-node flags resolve."""
    n = OrgNode(id=w.menu.id, parent_id=None, role="STOREFRONT", depth=0, path=w.menu.id,
                sells=True, is_settlement_boundary=True, is_loyalty_domain=True,
                loyalty_domain_id=w.merchant_id, settlement_account_id=w.merchant_id, **flags)
    db.add(n)
    db.commit()
    return n


def test_resolve_modules_cascade(db):
    build_breadtalk(db)
    sf = db.get(OrgNode, "o_bt_ion")        # a storefront under tenant m1
    tenant = db.get(OrgNode, "m1")
    sib = db.get(OrgNode, "o_tb_tamp")      # another storefront under m1
    assert sf is not None and tenant is not None and "m1" in sf.path.split(".")

    # Nothing set anywhere → legacy defaults (all three modules ON).
    r = boundaries.resolve_modules(db, node=sf, merchant_id="m1")
    assert r == {"rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": True}

    # Turn POS OFF at the tenant → every storefront in the subtree inherits OFF.
    tenant.mod_pos = False
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["pos_enabled"] is False
    assert boundaries.resolve_modules(db, node=sib, merchant_id="m1")["pos_enabled"] is False

    # A storefront overrides POS back ON → only it; the sibling still inherits the tenant's OFF.
    sf.mod_pos = True
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["pos_enabled"] is True
    assert boundaries.resolve_modules(db, node=sib, merchant_id="m1")["pos_enabled"] is False

    # Other flags untouched by the pos override.
    out = boundaries.resolve_modules(db, node=sf, merchant_id="m1")
    assert out["rewards_enabled"] is True and out["qr_ordering_enabled"] is True

    # node=None → pure legacy fallback (all three default ON).
    assert boundaries.resolve_modules(db, node=None, merchant_id="m1") == {
        "rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": True}


# --- A2: enforcement reads the node cascade (override beats the merchant default) ---------------
def test_node_override_disables_earn(client, db):
    w = make_world(db, earn_rate=1)
    _attach_node(db, w, mod_rewards=False)        # Engagement OFF at the node (settings still default on)
    cust = register_customer(client, email="ne1@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])
    assert res["points_earned"] == 0              # node override → no accrual


def test_node_override_disables_qr_ordering(client, db):
    w = make_world(db)
    _attach_node(db, w, mod_qr_ordering=False)     # Table QR OFF at the node
    cust = register_customer(client, email="nq1@b.sg")
    r = client.post("/api/v1/orders",
                    json={"qr_token": w.qr_token, "items": [{"menu_item_id": w.burger_id, "quantity": 1}]},
                    headers=H(cust["access_token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "ordering_disabled"
