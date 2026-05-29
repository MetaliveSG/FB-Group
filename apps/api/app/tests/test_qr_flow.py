"""Module 3 — QR Dining Flow."""
from app.tests.factories import make_world


def test_valid_qr_opens_correct_menu(client, db):
    w = make_world(db)
    r = client.get(f"/api/v1/qr/{w.qr_token}")
    assert r.status_code == 200
    body = r.json()
    assert body["merchant"]["id"] == w.merchant_id
    assert body["outlet"]["id"] == w.outlet_id
    assert body["table"]["label"] == "T01"
    names = [i["name"] for cat in body["menu"]["categories"] for i in cat["items"]]
    assert "Burger" in names


def test_invalid_qr_rejected(client, db):
    make_world(db)
    r = client.get("/api/v1/qr/DOES-NOT-EXIST")
    assert r.status_code == 404 and r.json()["error"]["code"] == "invalid_qr"


def test_outlet_isolation_via_qr(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    c1 = client.get(f"/api/v1/qr/{w1.qr_token}").json()
    c2 = client.get(f"/api/v1/qr/{w2.qr_token}").json()
    assert c1["merchant"]["id"] != c2["merchant"]["id"]
    assert c1["outlet"]["id"] == w1.outlet_id
    assert c2["outlet"]["id"] == w2.outlet_id
