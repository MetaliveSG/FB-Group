"""Merchant-wide orders feed — GET /orders (staff, merchant-scoped, outlet-limited)."""
from app.tests.factories import add_outlet, make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _placed(client, qr_token, item_id, email):
    cust = register_customer(client, email=email)
    order = place_order(client, cust["access_token"], qr_token, [{"menu_item_id": item_id, "quantity": 2}])
    checkout(client, cust["access_token"], order["id"])
    return order


def test_owner_sees_orders_with_items_and_labels(client, db):
    w = make_world(db)
    _placed(client, w.qr_token, w.burger_id, "f1@b.sg")
    owner = staff_token(client, w.owner_email)
    feed = client.get("/api/v1/orders", headers=H(owner)).json()
    assert len(feed) == 1
    o = feed[0]
    assert o["items"] and o["items"][0]["quantity"] == 2
    assert o["outlet_name"] and o["customer_name"]  # resolved labels
    assert o["total"] > 0 and "subtotal" in o


def test_status_filter(client, db):
    w = make_world(db)
    _placed(client, w.qr_token, w.burger_id, "f2@b.sg")  # → completed
    owner = staff_token(client, w.owner_email)
    assert len(client.get("/api/v1/orders?status=completed", headers=H(owner)).json()) == 1
    assert client.get("/api/v1/orders?status=pending", headers=H(owner)).json() == []


def test_outlet_scoped_user_only_sees_their_outlet(client, db):
    w = make_world(db)             # outlet A + outlet_mgr scoped to A
    o2 = add_outlet(db, w, "B")    # outlet B (same merchant)
    _placed(client, o2.qr_token, o2.item_id, "f3@b.sg")  # order at outlet B

    owner = staff_token(client, w.owner_email)
    mgr_a = staff_token(client, w.outlet_mgr_email)
    assert len(client.get("/api/v1/orders", headers=H(owner)).json()) == 1   # owner sees all outlets
    assert client.get("/api/v1/orders", headers=H(mgr_a)).json() == []       # A-manager sees none of B's


def test_cross_merchant_blocked(client, db):
    a = make_world(db, name="OFeedA", token_suffix="OA")
    b = make_world(db, name="OFeedB", token_suffix="OB")
    owner_a = staff_token(client, a.owner_email)
    r = client.get(f"/api/v1/orders?merchant_id={b.merchant_id}", headers=H(owner_a))
    assert r.status_code == 403
