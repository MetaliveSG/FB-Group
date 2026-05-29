"""Customer rewards center + spin-the-wheel."""
from app.loyalty.engine import get_or_create_account, tier_for
from app.models.engagement import RewardCatalogItem, WheelSegment
from app.services.rewards import WHEEL_SPIN_COST
from app.models.enums import RewardScope
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer


def _give_points(db, world, customer_id, pts):
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=world.merchant_id)
    acct.points_balance = pts
    acct.lifetime_points = pts
    acct.tier = tier_for(pts)
    db.commit()


def _add_catalog(db, world, name="Free Drink", cost=100):
    item = RewardCatalogItem(merchant_id=world.merchant_id, name=name, kind="free_item", cost_points=cost)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _add_wheel(db, world):
    segs = [("10 pts", "points", 10, 1, "#f00"), ("Try again", "nothing", 0, 1, "#aaa"),
            ("50 pts", "points", 50, 1, "#0f0")]
    for i, (l, k, v, w, col) in enumerate(segs):
        db.add(WheelSegment(merchant_id=world.merchant_id, label=l, prize_kind=k, prize_value=v,
                            weight=w, color=col, sort_order=i))
    db.commit()


def test_loyalty_summary(client, db):
    w = make_world(db)
    cust = register_customer(client, email="r1@b.sg")
    _give_points(db, w, cust["customer"]["id"], 600)  # >=500 -> silver
    r = client.get(f"/api/v1/me/loyalty?merchant_id={w.merchant_id}", headers=H(cust["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["points_balance"] == 600
    assert body["tier"] == "silver" and body["next_tier"] == "gold"
    assert body["points_to_next_tier"] == 1400  # 2000 - 600


def test_redeem_catalog_item(client, db):
    w = make_world(db)
    cust = register_customer(client, email="r2@b.sg")
    item = _add_catalog(db, w, cost=100)
    _give_points(db, w, cust["customer"]["id"], 250)
    r = client.post("/api/v1/me/rewards/redeem",
                    json={"merchant_id": w.merchant_id, "item_id": item.id}, headers=H(cust["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["voucher_code"].startswith("VCH-") and body["points_balance"] == 150


def test_redeem_insufficient_blocked(client, db):
    w = make_world(db)
    cust = register_customer(client, email="r3@b.sg")
    item = _add_catalog(db, w, cost=500)
    _give_points(db, w, cust["customer"]["id"], 100)
    r = client.post("/api/v1/me/rewards/redeem",
                    json={"merchant_id": w.merchant_id, "item_id": item.id}, headers=H(cust["access_token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_points"


def test_wheel_spin_deducts_and_awards(client, db):
    w = make_world(db)
    _add_wheel(db, w)
    cust = register_customer(client, email="r4@b.sg")
    _give_points(db, w, cust["customer"]["id"], 200)
    cfg = client.get(f"/api/v1/me/wheel?merchant_id={w.merchant_id}", headers=H(cust["access_token"])).json()
    assert cfg["spin_cost"] == WHEEL_SPIN_COST and len(cfg["segments"]) == 3
    r = client.post("/api/v1/me/wheel/spin", json={"merchant_id": w.merchant_id}, headers=H(cust["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["winning_index"] < 3
    # 200 - spin cost + prize (>=0) -> at least (200 - cost)
    assert body["points_balance"] >= 200 - WHEEL_SPIN_COST


def test_wheel_insufficient_blocked(client, db):
    w = make_world(db)
    _add_wheel(db, w)
    cust = register_customer(client, email="r5@b.sg")
    _give_points(db, w, cust["customer"]["id"], WHEEL_SPIN_COST - 1)  # always just under cost
    r = client.post("/api/v1/me/wheel/spin", json={"merchant_id": w.merchant_id}, headers=H(cust["access_token"]))
    assert r.status_code == 409
