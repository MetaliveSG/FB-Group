"""Loyalty-program admin — merchant self-serve earn rules (the gap behind Bedok's 0 coins)."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def test_get_program_reflects_seeded_rules(client, db):
    w = make_world(db, earn_rate=1)  # seeds earn=1pt/$ + welcome 50
    owner = staff_token(client, w.owner_email)
    prog = client.get("/api/v1/org/loyalty", headers=H(owner)).json()
    assert prog["points_per_dollar"] == 1.0
    assert prog["welcome_bonus"] == 50
    assert prog["birthday_bonus"] == 0  # not seeded


def test_update_program_then_orders_earn_new_rate(client, db):
    w = make_world(db, earn_rate=1)
    owner = staff_token(client, w.owner_email)
    r = client.put("/api/v1/org/loyalty", headers=H(owner),
                   json={"points_per_dollar": 2, "welcome_bonus": 100, "birthday_bonus": 25})
    assert r.status_code == 200 and r.json()["points_per_dollar"] == 2.0

    cust = register_customer(client, email="lp@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])
    # 2pt/$ on the total + 100 first-visit → clearly more than the old 1pt/$ + 50 would give
    assert res["points_earned"] >= 100 + int(2 * order["total"])


def test_earn_rate_zero_disables_earning(client, db):
    w = make_world(db, earn_rate=1)
    owner = staff_token(client, w.owner_email)
    client.put("/api/v1/org/loyalty", headers=H(owner),
               json={"points_per_dollar": 0, "welcome_bonus": 0, "birthday_bonus": 0})
    cust = register_customer(client, email="z@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])
    assert res["points_earned"] == 0


def test_staff_cannot_update_program(client, db):
    w = make_world(db)
    staff = staff_token(client, w.staff_email)  # lacks merchant.manage (and report.view)
    r = client.put("/api/v1/org/loyalty", headers=H(staff),
                   json={"points_per_dollar": 5, "welcome_bonus": 0, "birthday_bonus": 0})
    assert r.status_code == 403


def test_cannot_update_other_merchant_program(client, db):
    a = make_world(db, name="LpA", token_suffix="LA")
    b = make_world(db, name="LpB", token_suffix="LB")
    owner_a = staff_token(client, a.owner_email)
    r = client.put(f"/api/v1/org/loyalty?merchant_id={b.merchant_id}", headers=H(owner_a),
                   json={"points_per_dollar": 9, "welcome_bonus": 0, "birthday_bonus": 0})
    assert r.status_code == 403


def test_module_flags_via_settings_endpoint(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)
    out = client.patch("/api/v1/org/settings", headers=H(owner),
                       json={"qr_ordering_enabled": False, "pos_enabled": True}).json()
    assert out["qr_ordering_enabled"] is False and out["pos_enabled"] is True
    assert out["rewards_enabled"] is True  # untouched default
