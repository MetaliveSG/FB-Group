"""POS receipt: company header (console-configured) + outlet/stall + lines + payment; and the staff
endpoint listing an attached diner's unused vouchers."""
from app.services import vouchers
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer, staff_token


def _manual_order(client, t, w, phone=None):
    body = {"outlet_id": w.outlet_id, "items": [{"menu_item_id": w.burger_id, "quantity": 1}]}
    if phone:
        body["customer_phone"] = phone
    r = client.post("/api/v1/orders/manual", json=body, headers=H(t))
    assert r.status_code == 201, r.text
    return r.json()


def test_receipt_payload_with_company_header(client, db):
    w = make_world(db)
    t = staff_token(client, w.owner_email)
    client.patch("/api/v1/org/settings", json={"receipt": {
        "company_name": "Acme Pte Ltd", "uen": "201912345A", "address": "1 Test St",
        "phone": "61234567", "footer": "See you!"}}, headers=H(t))
    o = _manual_order(client, t, w)
    client.post(f"/api/v1/orders/{o['id']}/cashier-checkout", json={"method": "cash"}, headers=H(t))
    rec = client.get(f"/api/v1/orders/{o['id']}/receipt", headers=H(t))
    assert rec.status_code == 200, rec.text
    d = rec.json()
    assert d["company"]["name"] == "Acme Pte Ltd" and d["company"]["uen"] == "201912345A"
    assert d["outlet"]["name"] == w.outlet.name
    assert len(d["items"]) == 1 and d["items"][0]["quantity"] == 1
    assert d["payment"]["method"] == "cash" and d["payment"]["status"] == "success"
    assert d["footer"] == "See you!"


def test_receipt_company_falls_back_to_merchant_name(client, db):
    w = make_world(db)
    t = staff_token(client, w.owner_email)
    o = _manual_order(client, t, w)
    d = client.get(f"/api/v1/orders/{o['id']}/receipt", headers=H(t)).json()
    assert d["company"]["name"] == w.merchant.name   # no config → merchant name


def test_staff_lists_diner_unused_vouchers(client, db):
    w = make_world(db)
    t = staff_token(client, w.owner_email)
    cust = register_customer(client, email="dv@b.sg", phone="+6590000701")
    vouchers.issue_vouchers(db, customer_id=cust["customer"]["id"], merchant_id=w.merchant_id,
                            name="$1 off", value=1)
    db.commit()
    r = client.get(f"/api/v1/vouchers/diner/{cust['customer']['id']}?merchant_id={w.merchant_id}", headers=H(t))
    assert r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["status"] == "issued"
