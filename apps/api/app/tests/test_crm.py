"""Module 7 — CRM Dashboard."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _capture_one_customer(client, w, email="diner@b.sg", qty=1):
    tok = register_customer(client, email=email)["access_token"]
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": w.burger_id, "quantity": qty}])
    res = checkout(client, tok, order["id"])
    return tok, res


def test_customer_record_updates_after_order(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    # Before: CRM empty.
    assert client.get("/api/v1/crm/customers", headers=H(otok)).json() == []

    _capture_one_customer(client, w)

    custs = client.get("/api/v1/crm/customers", headers=H(otok)).json()
    assert len(custs) == 1
    c = custs[0]
    assert c["visit_count"] == 1 and c["total_spend"] > 0 and c["points_balance"] > 0


def test_segmentation_new_customer(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    _capture_one_customer(client, w)
    custs = client.get("/api/v1/crm/customers", headers=H(otok)).json()
    assert "new" in custs[0]["segments"]


def test_filter_customers_by_segment(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    _capture_one_customer(client, w)
    new = client.get("/api/v1/crm/customers?segment=new", headers=H(otok)).json()
    vip = client.get("/api/v1/crm/customers?segment=vip", headers=H(otok)).json()
    assert len(new) == 1 and len(vip) == 0


def test_customer_profile_has_histories(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cust = register_customer(client, email="profile@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])

    prof = client.get(f"/api/v1/crm/customers/{cust['customer']['id']}", headers=H(otok)).json()
    assert prof["metrics"]["visit_count"] == 1
    assert prof["metrics"]["points_balance"] == res["points_earned"]
    assert len(prof["transactions"]) == 1
    assert len(prof["orders"]) == 1
    assert len(prof["rewards"]) >= 1


def test_cross_merchant_data_leakage_blocked(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    # A customer transacts only at M2.
    _capture_one_customer(client, w2, email="m2cust@b.sg")

    owner1 = staff_token(client, w1.owner_email)
    # M1 owner sees none of M2's customers.
    assert client.get("/api/v1/crm/customers", headers=H(owner1)).json() == []
    # And cannot query M2 explicitly.
    forb = client.get(f"/api/v1/crm/customers?merchant_id={w2.merchant_id}", headers=H(owner1))
    assert forb.status_code == 403


def test_tags_and_notes(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cust = register_customer(client, email="tagme@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])
    cid = cust["customer"]["id"]

    t = client.post(f"/api/v1/crm/customers/{cid}/tags", json={"tag": "loyal"}, headers=H(otok))
    assert t.status_code == 201
    n = client.post(f"/api/v1/crm/customers/{cid}/notes", json={"body": "Prefers window seat"}, headers=H(otok))
    assert n.status_code == 201

    prof = client.get(f"/api/v1/crm/customers/{cid}", headers=H(otok)).json()
    assert "loyal" in prof["tags"] and len(prof["notes"]) == 1
