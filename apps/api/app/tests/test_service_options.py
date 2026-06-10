"""Service options (fulfilment) — two axes: the storefront's enabled SET (cascade) decides the order's
dining context (order_type) AND hand-off; the diner picks one (auto if one). self_pickup → the diner
collects + "ready" alert; served → waiter brings it. Default = restaurant table service (back-compat)."""
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer, staff_token


def _attach(db, w, options):
    """A storefront node (id == menu.id) carrying an explicit enabled service-option set."""
    n = OrgNode(id=w.menu.id, parent_id=None, role="STOREFRONT", depth=0, path=w.menu.id,
                sells=True, is_settlement_boundary=True, is_loyalty_domain=True,
                loyalty_domain_id=w.merchant_id, settlement_account_id=w.merchant_id,
                mod_rewards=True, mod_qr_ordering=True, mod_pos=True, service_options=options)
    db.add(n)
    db.commit()
    return n


def _order(client, tok, w, **extra):
    return client.post("/api/v1/orders",
                       json={"qr_token": w.qr_token,
                             "items": [{"menu_item_id": w.burger_id, "quantity": 1}], **extra},
                       headers=H(tok))


def test_default_is_dine_in_self_service(client, db):
    """SEA-first default: an unconfigured storefront is dine-in SELF-SERVICE (diner collects) + takeaway."""
    w = make_world(db)
    cust = register_customer(client, email="so1@b.sg")
    r = _order(client, cust["access_token"], w)
    assert r.status_code == 201
    assert r.json()["order_type"] == "dine_in" and r.json()["hand_off"] == "self_pickup"


def test_storefront_pickup_drives_handoff(client, db):
    w = make_world(db)
    _attach(db, w, ["dine_in_pickup"])           # foodcourt: eat-in but self-collect
    cust = register_customer(client, email="so2@b.sg")
    r = _order(client, cust["access_token"], w)
    assert r.status_code == 201
    assert r.json()["order_type"] == "dine_in" and r.json()["hand_off"] == "self_pickup"


def test_takeaway_option(client, db):
    w = make_world(db)
    _attach(db, w, ["takeaway"])
    cust = register_customer(client, email="so3@b.sg")
    r = _order(client, cust["access_token"], w)
    assert r.json()["order_type"] == "takeaway" and r.json()["hand_off"] == "self_pickup"


def test_unavailable_option_rejected(client, db):
    w = make_world(db)
    _attach(db, w, ["dine_in_served"])
    cust = register_customer(client, email="so4@b.sg")
    r = _order(client, cust["access_token"], w, service_option="takeaway")   # not offered here
    assert r.status_code == 409 and r.json()["error"]["code"] == "service_option_unavailable"


def test_qr_context_lists_enabled_options(client, db):
    w = make_world(db)
    _attach(db, w, ["dine_in_pickup", "takeaway"])
    ctx = client.get(f"/api/v1/qr/{w.qr_token}").json()
    assert [o["key"] for o in ctx["service_options"]] == ["dine_in_pickup", "takeaway"]
    assert ctx["service_options"][0]["hand_off"] == "self_pickup"


def test_node_service_options_endpoint(client, db):
    build_breadtalk(db)
    ceo = H(staff_token(client, "ceo@breadtalk.sg"))
    g = client.get("/api/v1/org/nodes/o_bt_ion/service-options", headers=ceo).json()
    assert g["own"] is None and g["resolved"] == ["dine_in_pickup", "takeaway"]   # SEA-first default
    assert any(c["key"] == "takeaway" for c in g["catalog"])
    s = client.put("/api/v1/org/nodes/o_bt_ion/service-options",
                   json={"options": ["dine_in_served"]}, headers=ceo).json()       # flip to restaurant served
    assert s["own"] == ["dine_in_served"] and s["resolved"] == ["dine_in_served"]
    c = client.put("/api/v1/org/nodes/o_bt_ion/service-options", json={"options": []}, headers=ceo).json()
    assert c["own"] is None and c["resolved"] == ["dine_in_pickup", "takeaway"]    # cleared → inherit default
