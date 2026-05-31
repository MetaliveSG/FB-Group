"""Phase 2a — module flags gate behaviour (rewards / qr_ordering).

Defaults (rewards on, qr on) keep current behaviour; flipping a flag changes it. Gating lives
in the service layer (single source) and is per-merchant (tenant-scoped).
"""
from app.services import merchant_settings
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer


def _set(db, merchant_id, **flags):
    merchant_settings.update_settings(db, merchant_id=merchant_id, changes=flags)
    db.commit()


def test_rewards_enabled_default_earns_points(client, db):
    w = make_world(db, earn_rate=1)
    cust = register_customer(client, email="r1@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])
    assert res["points_earned"] > 0  # rewards on by default


def test_rewards_disabled_earns_zero(client, db):
    w = make_world(db, earn_rate=1)
    _set(db, w.merchant_id, rewards_enabled=False)
    cust = register_customer(client, email="r2@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])
    assert res["points_earned"] == 0  # loyalty module off → no accrual


def test_qr_ordering_disabled_rejects_order(client, db):
    w = make_world(db)
    _set(db, w.merchant_id, qr_ordering_enabled=False)
    cust = register_customer(client, email="o1@b.sg")
    r = client.post("/api/v1/orders",
                    json={"qr_token": w.qr_token, "items": [{"menu_item_id": w.burger_id, "quantity": 1}]},
                    headers=H(cust["access_token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "ordering_disabled"


def test_qr_context_exposes_flags(client, db):
    w = make_world(db)
    _set(db, w.merchant_id, qr_ordering_enabled=False, rewards_enabled=True)
    ctx = client.get(f"/api/v1/qr/{w.qr_token}").json()
    assert ctx["ordering_enabled"] is False
    assert ctx["rewards_enabled"] is True
    assert ctx["menu"] is None  # no inline menu when ordering is off


def test_gating_is_per_merchant(client, db):
    a = make_world(db, name="GateA", token_suffix="GA")
    b = make_world(db, name="GateB", token_suffix="GB")
    _set(db, a.merchant_id, qr_ordering_enabled=False)  # only A disabled
    # B (default on) still accepts orders
    cust = register_customer(client, email="g@b.sg")
    order = place_order(client, cust["access_token"], b.qr_token, [{"menu_item_id": b.burger_id, "quantity": 1}])
    assert order["id"]
    # A rejects
    r = client.post("/api/v1/orders",
                    json={"qr_token": a.qr_token, "items": [{"menu_item_id": a.burger_id, "quantity": 1}]},
                    headers=H(cust["access_token"]))
    assert r.status_code == 409
