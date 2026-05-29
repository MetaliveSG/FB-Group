"""Module 5 — Checkout & Simulated Payment; Module 6 — Loyalty & Rewards Engine."""
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError
from app.loyalty.engine import accrue_on_transaction, get_or_create_account, redeem
from app.models.enums import RewardRuleType, RewardScope
from app.models.identity import Customer
from app.models.loyalty import Coalition, LoyaltyAccount, RewardRule, coalition_members
from app.models.orders import Order
from app.models.payments import Transaction
from app.tests.factories import make_world
from app.tests.helpers import checkout, place_order, register_customer


def test_successful_payment_creates_transaction_and_points(client, db):
    w = make_world(db, earn_rate=1)
    tok = register_customer(client)["access_token"]
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    # burger 10 -> service 1.0 -> tax (11)*0.09=0.99 -> total 11.99
    res = checkout(client, tok, order["id"], method="paynow")
    assert res["payment"]["status"] == "success"
    assert res["transaction_id"] is not None
    # base = int(11.99 * 1) = 11 ; first-visit bonus 50 -> 61
    assert res["points_earned"] == 61

    txn = db.scalar(select(Transaction).where(Transaction.order_id == order["id"]))
    assert txn is not None and txn.customer_id and txn.outlet_id == w.outlet_id

    # Paid order is marked completed (no longer "pending" in order history).
    paid = db.get(Order, order["id"])
    assert paid.status == "completed" and paid.completed_at is not None


def test_failed_payment_issues_no_rewards(client, db):
    w = make_world(db)
    cust = register_customer(client)
    tok = cust["access_token"]
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, tok, order["id"], method="card", force_outcome="fail")
    assert res["payment"]["status"] == "failed"
    assert res["transaction_id"] is None
    assert res["points_earned"] == 0
    # No transaction and no loyalty account created.
    assert db.scalar(select(Transaction).where(Transaction.order_id == order["id"])) is None
    acct = db.scalar(select(LoyaltyAccount).where(LoyaltyAccount.customer_id == cust["customer"]["id"]))
    assert acct is None
    # Failed payment leaves the order pending (not completed).
    assert db.get(Order, order["id"]).status == "pending"


def test_double_checkout_blocked(client, db):
    w = make_world(db)
    tok = register_customer(client)["access_token"]
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, tok, order["id"])
    again = client.post(f"/api/v1/orders/{order['id']}/checkout",
                        json={"method": "paynow"}, headers={"Authorization": f"Bearer {tok}"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_paid"


def test_insufficient_points_blocks_redemption(db):
    w = make_world(db)
    c = Customer(full_name="Redeemer")
    db.add(c)
    db.flush()
    acct = get_or_create_account(db, customer_id=c.id, scope_type=RewardScope.MERCHANT.value, scope_id=w.merchant_id)
    acct.points_balance = 20
    db.flush()
    with pytest.raises(ConflictError):
        redeem(db, account=acct, reward_name="Free Drink", points=100)


def test_redeem_deducts_points(db):
    w = make_world(db)
    c = Customer(full_name="Redeemer")
    db.add(c)
    db.flush()
    acct = get_or_create_account(db, customer_id=c.id, scope_type=RewardScope.MERCHANT.value, scope_id=w.merchant_id)
    acct.points_balance = 100
    db.flush()
    redeem(db, account=acct, reward_name="Free Drink", points=30)
    assert acct.points_balance == 70


def test_campaign_multiplier_applies(db):
    w = make_world(db, earn_rate=1)
    db.add(RewardRule(scope_type=RewardScope.MERCHANT.value, scope_id=w.merchant_id, code="2x",
                      rule_type=RewardRuleType.CAMPAIGN_MULTIPLIER.value, config={"multiplier": 2.0},
                      is_active=True))
    db.flush()
    c = Customer(full_name="Booster")
    db.add(c)
    db.flush()
    pts = accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=None)
    # (base 100 + first-visit 50) * 2 = 300
    assert pts == 300


def test_merchant_isolated_vs_coalition_rewards(db):
    w = make_world(db, name="Coal", earn_rate=1)
    coalition = Coalition(name="Coalition")
    db.add(coalition)
    db.flush()
    db.execute(coalition_members.insert().values(coalition_id=coalition.id, merchant_id=w.merchant_id))
    db.add(RewardRule(scope_type=RewardScope.COALITION.value, scope_id=coalition.id, code="c-earn",
                      rule_type=RewardRuleType.EARN_RATE.value, config={"points_per_dollar": 0.5},
                      is_active=True))
    db.flush()

    c = Customer(full_name="Member")
    db.add(c)
    db.flush()
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=None)

    merchant_acct = db.scalar(select(LoyaltyAccount).where(
        LoyaltyAccount.customer_id == c.id, LoyaltyAccount.scope_type == RewardScope.MERCHANT.value))
    coalition_acct = db.scalar(select(LoyaltyAccount).where(
        LoyaltyAccount.customer_id == c.id, LoyaltyAccount.scope_type == RewardScope.COALITION.value))

    assert merchant_acct.points_balance == 150     # 100 base + 50 first-visit
    assert coalition_acct.points_balance == 50      # 100 * 0.5, separate balance
    assert merchant_acct.id != coalition_acct.id
