"""Menu management, user management, and RFM analytics."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


# --- Menu management ---------------------------------------------------
def test_menu_crud_flow(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    menu_id = w.menu.id

    cat = client.post("/api/v1/menu-admin/categories", json={"menu_id": menu_id, "name": "Desserts"}, headers=H(otok))
    assert cat.status_code == 201
    cat_id = cat.json()["id"]

    item = client.post("/api/v1/menu-admin/items",
                       json={"category_id": cat_id, "name": "Ice Cream", "price": 4.5}, headers=H(otok))
    assert item.status_code == 201
    item_id = item.json()["id"]

    # New item shows up in the public menu read.
    menu = client.get(f"/api/v1/outlets/{w.outlet_id}/menu").json()
    names = [i["name"] for c in menu["categories"] for i in c["items"]]
    assert "Ice Cream" in names

    upd = client.patch(f"/api/v1/menu-admin/items/{item_id}", json={"is_available": False}, headers=H(otok))
    assert upd.status_code == 200 and upd.json()["is_available"] is False

    mod = client.post("/api/v1/menu-admin/modifiers",
                      json={"item_id": item_id, "name": "Extra scoop", "price_delta": 1.5}, headers=H(otok))
    assert mod.status_code == 201

    assert client.delete(f"/api/v1/menu-admin/items/{item_id}", headers=H(otok)).status_code == 204


def test_menu_tenant_isolation(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    make_world(db, name="M2", token_suffix="2")
    o2 = staff_token(client, "owner@m2.sg")
    r = client.post("/api/v1/menu-admin/categories", json={"menu_id": w1.menu.id, "name": "Hack"}, headers=H(o2))
    assert r.status_code in (403, 404)


# --- User management ---------------------------------------------------
def test_invite_list_revoke_user(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    inv = client.post("/api/v1/admin/users",
                      json={"email": "newstaff@m.sg", "password": "Password123!", "full_name": "New Staff",
                            "role": "staff", "scope_type": "outlet", "scope_id": w.outlet_id}, headers=H(otok))
    assert inv.status_code == 201
    # invited user can authenticate
    assert staff_token(client, "newstaff@m.sg")

    users = client.get("/api/v1/admin/users", headers=H(otok)).json()
    target = next(u for u in users if u["email"] == "newstaff@m.sg")
    assert target["roles"][0]["role"] == "staff"

    # duplicate email rejected
    dup = client.post("/api/v1/admin/users",
                      json={"email": "newstaff@m.sg", "password": "Password123!", "role": "staff",
                            "scope_type": "merchant"}, headers=H(otok))
    assert dup.status_code == 409

    aid = target["roles"][0]["assignment_id"]
    assert client.delete(f"/api/v1/admin/users/assignments/{aid}", headers=H(otok)).status_code == 204


def test_user_management_requires_permission(client, db):
    w = make_world(db)
    mgr = staff_token(client, w.outlet_mgr_email)  # outlet manager lacks user.manage
    assert client.get("/api/v1/admin/users", headers=H(mgr)).status_code == 403


def test_invite_scope_isolation(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    o1 = staff_token(client, "owner@m1.sg")
    # M1 owner cannot place a user into M2's outlet
    r = client.post("/api/v1/admin/users",
                    json={"email": "x@m.sg", "password": "Password123!", "role": "staff",
                          "scope_type": "outlet", "scope_id": w2.outlet_id}, headers=H(o1))
    assert r.status_code == 403


# --- RFM analytics -----------------------------------------------------
def test_rfm_scoring(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    for i in range(3):
        cust = register_customer(client, email=f"rfm{i}@b.sg")
        order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": i + 1}])
        checkout(client, cust["access_token"], order["id"])

    rfm = client.get("/api/v1/reports/rfm", headers=H(otok)).json()
    assert rfm["count"] == 3
    assert all(1 <= c["r"] <= 5 and 1 <= c["f"] <= 5 and 1 <= c["m"] <= 5 and c["segment"] for c in rfm["customers"])
    assert sum(rfm["distribution"].values()) == 3
