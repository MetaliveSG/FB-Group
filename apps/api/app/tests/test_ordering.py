"""Module 4 — Menu & Ordering."""
from app.tests.factories import make_world
from app.tests.helpers import H, place_order, register_customer, staff_token


def test_place_order_computes_totals(client, db):
    w = make_world(db)
    tok = register_customer(client)["access_token"]
    order = place_order(client, tok, w.qr_token, [
        {"menu_item_id": w.burger_id, "quantity": 2, "modifier_ids": [w.cheese_id]},
        {"menu_item_id": w.drink_id, "quantity": 1},
    ])
    # (burger 10 + cheese 2) * 2 = 24 ; drink 5 -> subtotal 29
    assert order["subtotal"] == 29.0
    assert order["service_charge"] == 2.9            # 10% dine-in
    assert order["tax"] == 2.87                      # 9% GST of (29 + 2.9)
    assert order["total"] == 34.77
    assert order["status"] == "pending"


def test_invalid_item_rejected(client, db):
    w = make_world(db)
    tok = register_customer(client)["access_token"]
    r = client.post("/api/v1/orders",
                    json={"qr_token": w.qr_token, "items": [{"menu_item_id": "ghost", "quantity": 1}]},
                    headers=H(tok))
    assert r.status_code == 404


def test_unavailable_item_rejected(client, db):
    w = make_world(db)
    tok = register_customer(client)["access_token"]
    r = client.post("/api/v1/orders",
                    json={"qr_token": w.qr_token, "items": [{"menu_item_id": w.unavailable_id, "quantity": 1}]},
                    headers=H(tok))
    assert r.status_code == 409 and r.json()["error"]["code"] == "item_unavailable"


def test_order_status_lifecycle(client, db):
    w = make_world(db)
    tok = register_customer(client)["access_token"]
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    stok = staff_token(client, w.staff_email)

    ok = client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "accepted"}, headers=H(stok))
    assert ok.status_code == 200 and ok.json()["status"] == "accepted"

    # Illegal jump accepted -> completed (must pass through preparing/ready).
    bad = client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "completed"}, headers=H(stok))
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "invalid_transition"


def test_manual_cashier_order_supported(client, db):
    w = make_world(db)
    stok = staff_token(client, w.staff_email)
    r = client.post("/api/v1/orders/manual",
                    json={"outlet_id": w.outlet_id, "customer_phone": "+6590001111",
                          "items": [{"menu_item_id": w.burger_id, "quantity": 1}]},
                    headers=H(stok))
    assert r.status_code == 201
    assert r.json()["channel"] == "cashier"
