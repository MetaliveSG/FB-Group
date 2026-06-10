"""Kitchen display (KDS) — the paid, not-yet-collected queue + the fulfilment lifecycle
(queued→preparing→ready→collected). READY = ready for pick-up. Separate from payment `status`."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _paid_order(client, db, w, email):
    cust = register_customer(client, email=email)
    order = place_order(client, cust["access_token"], w.qr_token,
                        [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])   # → status COMPLETED, fulfilment QUEUED
    return order


def test_kitchen_queue_and_pickup_flow(client, db):
    w = make_world(db, earn_rate=1)
    order = _paid_order(client, db, w, "kd1@b.sg")
    own = H(staff_token(client, w.owner_email))
    kitchen = f"/api/v1/orders/kitchen?outlet_id={w.outlet_id}"

    # A paid order shows on the kitchen queue, queued.
    q = client.get(kitchen, headers=own).json()
    assert len(q) == 1 and q[0]["id"] == order["id"] and q[0]["fulfilment_status"] == "queued"
    assert q[0]["status"] == "completed"            # paid; payment status is separate
    assert q[0]["items"]                            # tickets carry their line items

    # Advance queued → preparing → ready (ready for pick-up).
    r = client.patch(f"/api/v1/orders/{order['id']}/fulfilment", json={"status": "preparing"}, headers=own)
    assert r.status_code == 200 and r.json()["fulfilment_status"] == "preparing"
    r = client.patch(f"/api/v1/orders/{order['id']}/fulfilment", json={"status": "ready"}, headers=own)
    assert r.status_code == 200 and r.json()["fulfilment_status"] == "ready"
    # Still on the board while READY (waiting for the customer to collect).
    assert any(o["id"] == order["id"] for o in client.get(kitchen, headers=own).json())

    # Collected → leaves the queue.
    r = client.patch(f"/api/v1/orders/{order['id']}/fulfilment", json={"status": "collected"}, headers=own)
    assert r.status_code == 200 and r.json()["fulfilment_status"] == "collected"
    assert all(o["id"] != order["id"] for o in client.get(kitchen, headers=own).json())


def test_invalid_fulfilment_transition(client, db):
    w = make_world(db)
    order = _paid_order(client, db, w, "kd2@b.sg")
    own = H(staff_token(client, w.owner_email))
    # queued has no direct → collected (must pass through ready).
    r = client.patch(f"/api/v1/orders/{order['id']}/fulfilment", json={"status": "collected"}, headers=own)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_fulfilment_transition"


def test_kitchen_requires_staff(client, db):
    w = make_world(db)
    cust = register_customer(client, email="kd3@b.sg")
    # A customer token has no order.view → cannot read the kitchen queue.
    r = client.get(f"/api/v1/orders/kitchen?outlet_id={w.outlet_id}", headers=H(cust["access_token"]))
    assert r.status_code in (401, 403)
