"""Org-structure admin: brands -> outlets (auto-menu) -> tables/QR."""
from app.tests.factories import make_world
from app.tests.helpers import H, staff_token


def test_org_full_flow(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)

    brand = client.post("/api/v1/org/brands", json={"name": "New Brand", "cuisine_type": "Bakery"}, headers=H(otok))
    assert brand.status_code == 201
    bid = brand.json()["id"]

    outlet = client.post("/api/v1/org/outlets",
                         json={"brand_id": bid, "name": "New Outlet", "address": "1 Demo St"}, headers=H(otok))
    assert outlet.status_code == 201
    oid = outlet.json()["id"]
    assert outlet.json()["menu_id"]  # auto-created menu

    table = client.post(f"/api/v1/org/outlets/{oid}/tables", json={"label": "A1", "seats": 2}, headers=H(otok))
    assert table.status_code == 201
    token = table.json()["qr_token"]
    assert token

    # The freshly-minted QR token resolves to the new outlet (no app download).
    ctx = client.get(f"/api/v1/qr/{token}")
    assert ctx.status_code == 200 and ctx.json()["outlet"]["id"] == oid

    # Brand now reports 1 outlet.
    brands = client.get("/api/v1/org/brands", headers=H(otok)).json()
    assert next(b for b in brands if b["id"] == bid)["outlets"] == 1


def test_org_requires_permission(client, db):
    w = make_world(db)
    stok = staff_token(client, w.staff_email)  # staff lacks brand.manage/outlet.manage
    assert client.post("/api/v1/org/brands", json={"name": "X"}, headers=H(stok)).status_code == 403


def test_org_tenant_isolation(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    make_world(db, name="M2", token_suffix="2")
    o2 = staff_token(client, "owner@m2.sg")
    # M2 owner cannot attach an outlet to M1's brand
    r = client.post("/api/v1/org/outlets", json={"brand_id": w1.brand_id, "name": "Hack"}, headers=H(o2))
    assert r.status_code in (403, 404)


def test_table_label_unique(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    assert client.post(f"/api/v1/org/outlets/{w.outlet_id}/tables", json={"label": "Z9"}, headers=H(otok)).status_code == 201
    dup = client.post(f"/api/v1/org/outlets/{w.outlet_id}/tables", json={"label": "Z9"}, headers=H(otok))
    assert dup.status_code == 409
