"""Rewards-system hardening — fills gaps around the loyalty/wheel/jackpot/voucher
flow: progressive grand-jackpot pot (grow + persist + reset-on-win), multi-tenant
isolation of redemptions, voucher durability vs prize deletion, actor separation,
and drain-to-insufficient guardrails.

Mirrors conftest's isolated SQLite + TestClient. See test_jackpot.py / test_rewards.py
for the base-path coverage; this file is the adversarial / edge layer.
"""
from datetime import timedelta

from sqlalchemy import select

from app.db.base import utcnow
from app.loyalty.engine import get_or_create_account, tier_for
from app.models.engagement import JackpotPrize, RewardCatalogItem, WheelSegment
from app.models.enums import RewardScope
from app.models.loyalty import RewardRedemption
from app.models.tenancy import Merchant
from app.services import jackpot as jackpot_service
from app.services import rewards as rewards_service
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer, staff_token


# ── local seeders ───────────────────────────────────────────────────────────
def _give_coins(db, merchant_id, customer_id, coins):
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id)
    acct.points_balance = coins
    acct.lifetime_points = max(acct.lifetime_points, coins)
    acct.tier = tier_for(acct.lifetime_points)
    db.commit()
    return acct


def _seed_catalog(db, merchant_id, name="Free Coffee", cost=100):
    item = RewardCatalogItem(merchant_id=merchant_id, name=name, kind="free_item",
                             value=0, cost_points=cost, sort_order=0)
    db.add(item)
    db.commit()
    return item


def _seed_jackpot(db, merchant_id):
    for i, (n, p, e, w) in enumerate([("Teh Tarik", 2.2, "🥤", 5), ("Chendol", 3.0, "🍧", 4)]):
        db.add(JackpotPrize(merchant_id=merchant_id, item_name=n, item_price=p, emoji=e, weight=w, sort_order=i))
    db.commit()


# ── progressive grand jackpot ────────────────────────────────────────────────
def test_grand_jackpot_config_at_least_base(client, db):
    w = make_world(db)
    _seed_jackpot(db, w.merchant_id)
    cfg = jackpot_service.jackpot_config(db, merchant_id=w.merchant_id)
    assert cfg["grand_prize"] >= jackpot_service.GRAND_JACKPOT_BASE


def test_grand_jackpot_grows_with_elapsed_time(db):
    w = make_world(db)
    m = db.get(Merchant, w.merchant_id)
    # anchor the pot 200 seconds in the past → base + 200*rate
    m.settings = {**(m.settings or {}), "grand_jackpot_since": (utcnow() - timedelta(seconds=200)).isoformat()}
    db.commit()
    pot = jackpot_service._grand_prize(db, m)
    expected = jackpot_service.GRAND_JACKPOT_BASE + int(200 * jackpot_service.GRAND_JACKPOT_RATE)
    assert pot == expected
    assert pot > jackpot_service.GRAND_JACKPOT_BASE


def test_grand_jackpot_resets_to_base_on_win(db):
    w = make_world(db)
    m = db.get(Merchant, w.merchant_id)
    m.settings = {**(m.settings or {}), "grand_jackpot_since": (utcnow() - timedelta(hours=2)).isoformat()}
    db.commit()
    assert jackpot_service._grand_prize(db, m) > jackpot_service.GRAND_JACKPOT_BASE  # grown
    jackpot_service._reset_grand_prize(m)
    db.commit()
    # immediately after reset the pot is back to (approximately) base
    assert jackpot_service._grand_prize(db, m) == jackpot_service.GRAND_JACKPOT_BASE


def test_grand_jackpot_persists_across_reads(db):
    """The pot is anchored on first read and keeps growing from the SAME anchor —
    it must not reset to base on every read."""
    w = make_world(db)
    m = db.get(Merchant, w.merchant_id)
    first = jackpot_service._grand_prize(db, m)        # lazy-inits + commits the anchor
    since1 = (m.settings or {}).get("grand_jackpot_since")
    second = jackpot_service._grand_prize(db, m)
    since2 = (m.settings or {}).get("grand_jackpot_since")
    assert since1 == since2 and since1 is not None     # anchor stable (not re-init each read)
    assert second >= first                              # monotonic, not reset


# ── multi-tenant isolation ───────────────────────────────────────────────────
def test_redeem_rejects_item_from_another_merchant(client, db):
    m1 = make_world(db, name="M1", token_suffix="M1")
    m2 = make_world(db, name="M2", token_suffix="M2")
    item_m2 = _seed_catalog(db, m2.merchant_id, name="M2 Reward")
    cust = register_customer(client, email="iso@b.sg", phone="+6592000001")
    _give_coins(db, m1.merchant_id, cust["customer"]["id"], 9999)
    # Try to redeem M2's item while pointing at M1 → item.merchant_id != merchant_id → 404
    r = client.post("/api/v1/me/rewards/redeem",
                    json={"merchant_id": m1.merchant_id, "item_id": item_m2.id},
                    headers=H(cust["access_token"]))
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "reward_not_found"


def test_coins_balance_is_per_merchant_scope(client, db):
    """Coins earned at M1 must not be spendable at M2 (separate loyalty scopes)."""
    m1 = make_world(db, name="A1", token_suffix="A1")
    m2 = make_world(db, name="A2", token_suffix="A2")
    item_m2 = _seed_catalog(db, m2.merchant_id, name="A2 Reward", cost=50)
    cust = register_customer(client, email="scope@b.sg", phone="+6592000002")
    _give_coins(db, m1.merchant_id, cust["customer"]["id"], 9999)  # rich at M1 only
    # Redeem M2 item at M2 → customer has 0 coins in M2 scope → insufficient
    r = client.post("/api/v1/me/rewards/redeem",
                    json={"merchant_id": m2.merchant_id, "item_id": item_m2.id},
                    headers=H(cust["access_token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_points"


# ── voucher durability ───────────────────────────────────────────────────────
def test_voucher_survives_catalog_item_deletion(client, db):
    w = make_world(db)
    item = _seed_catalog(db, w.merchant_id, name="Free Kaya Toast", cost=80)
    cust = register_customer(client, email="vd@b.sg", phone="+6592000003")
    _give_coins(db, w.merchant_id, cust["customer"]["id"], 500)
    red = client.post("/api/v1/me/rewards/redeem",
                      json={"merchant_id": w.merchant_id, "item_id": item.id},
                      headers=H(cust["access_token"]))
    assert red.status_code == 200
    # Merchant later removes the catalog item.
    db.delete(db.get(RewardCatalogItem, item.id))
    db.commit()
    # The customer's voucher (name snapshot) still resolves.
    v = client.get(f"/api/v1/me/vouchers?merchant_id={w.merchant_id}", headers=H(cust["access_token"]))
    assert v.status_code == 200
    names = [x["reward_name"] for x in v.json()]
    assert "Free Kaya Toast" in names


# ── actor separation ─────────────────────────────────────────────────────────
def test_rewards_endpoint_rejects_staff_actor(client, db):
    w = make_world(db)
    stoken = staff_token(client, w.owner_email)  # a real staff (non-customer) actor
    r = client.get(f"/api/v1/me/loyalty?merchant_id={w.merchant_id}", headers=H(stoken))
    assert r.status_code in (401, 403), r.text


# ── drain-to-insufficient guardrail ─────────────────────────────────────────
def test_redeem_until_insufficient_then_blocked(client, db):
    w = make_world(db)
    item = _seed_catalog(db, w.merchant_id, name="Cheap Treat", cost=100)
    cust = register_customer(client, email="drain@b.sg", phone="+6592000004")
    _give_coins(db, w.merchant_id, cust["customer"]["id"], 250)  # affords 2, not 3
    ok1 = client.post("/api/v1/me/rewards/redeem", json={"merchant_id": w.merchant_id, "item_id": item.id}, headers=H(cust["access_token"]))
    ok2 = client.post("/api/v1/me/rewards/redeem", json={"merchant_id": w.merchant_id, "item_id": item.id}, headers=H(cust["access_token"]))
    blocked = client.post("/api/v1/me/rewards/redeem", json={"merchant_id": w.merchant_id, "item_id": item.id}, headers=H(cust["access_token"]))
    assert ok1.status_code == 200 and ok2.status_code == 200
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "insufficient_points"
    # exactly 2 vouchers minted, balance 50
    reds = db.scalars(select(RewardRedemption)).all()
    assert len([r for r in reds if r.reward_name == "Cheap Treat"]) == 2
