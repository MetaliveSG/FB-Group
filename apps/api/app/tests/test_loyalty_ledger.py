"""Phase 0a — the coin ledger as an append-only, domain-stamped posting substrate.

Guards three invariants that everything downstream (rollup, cross-domain fees, POS) relies on:
1. every posting carries its `loyalty_domain_id` (stamped at mint, = account scope);
2. the cached `points_balance` always equals `SUM(ledger)` — ledger is the source of truth;
3. accrual is idempotent per (account, order) — a replay never double-credits.
"""
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.loyalty.engine import (
    accrue_on_transaction,
    get_or_create_account,
    ledger_balance,
    record_reward_txn,
    redeem,
)
from app.models.enums import RewardScope, RewardTxnType
from app.models.identity import Customer
from app.models.loyalty import Coalition, LoyaltyAccount, RewardTransaction, coalition_members
from app.models.orders import Order
from app.tests.factories import make_world


def _customer(db, name="Ledger Cust"):
    c = Customer(full_name=name)
    db.add(c)
    db.flush()
    return c


def _order(db, w):
    """A minimal real Order so `order_id` satisfies the FK (SQLite FKs are ON in tests)."""
    o = Order(merchant_id=w.merchant_id, brand_id=w.brand_id, outlet_id=w.outlet_id)
    db.add(o)
    db.flush()
    return o


def _merchant_account(db, w, customer_id):
    return db.scalar(select(LoyaltyAccount).where(
        LoyaltyAccount.customer_id == customer_id,
        LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
        LoyaltyAccount.scope_id == w.merchant_id,
    ))


def test_every_posting_is_domain_stamped(db):
    w = make_world(db, earn_rate=1)
    c = _customer(db)
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=None)

    acct = _merchant_account(db, w, c.id)
    txns = db.scalars(select(RewardTransaction).where(RewardTransaction.account_id == acct.id)).all()
    assert txns, "accrual should have written ledger rows"
    # The stamp equals the account scope (merchant) — recorded at mint, not reconstructed.
    assert all(t.loyalty_domain_id == w.merchant_id for t in txns)


def test_coalition_postings_stamped_with_coalition_domain(db):
    w = make_world(db, name="Dom", earn_rate=1)
    coalition = Coalition(name="Ring")
    db.add(coalition)
    db.flush()
    db.execute(coalition_members.insert().values(coalition_id=coalition.id, merchant_id=w.merchant_id))
    # a coalition earn rule so the coalition account gets postings
    from app.models.loyalty import RewardRule
    from app.models.enums import RewardRuleType
    db.add(RewardRule(scope_type=RewardScope.COALITION.value, scope_id=coalition.id, code="c-earn",
                      rule_type=RewardRuleType.EARN_RATE.value, config={"points_per_dollar": 1}, is_active=True))
    db.flush()
    c = _customer(db)
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("50.00"), order_id=None)

    coalition_acct = db.scalar(select(LoyaltyAccount).where(
        LoyaltyAccount.customer_id == c.id, LoyaltyAccount.scope_type == RewardScope.COALITION.value))
    ctxns = db.scalars(select(RewardTransaction).where(RewardTransaction.account_id == coalition_acct.id)).all()
    assert ctxns and all(t.loyalty_domain_id == coalition.id for t in ctxns)


def test_balance_reconciles_to_ledger_through_earn_and_redeem(db):
    w = make_world(db, earn_rate=1)
    c = _customer(db)
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=None)
    acct = _merchant_account(db, w, c.id)
    # base 100 + first-visit 50
    assert acct.points_balance == 150
    assert ledger_balance(db, acct.id) == acct.points_balance

    redeem(db, account=acct, reward_name="Free coffee", points=50)
    assert acct.points_balance == 100
    # ledger sum (150 earned − 50 redeemed) must equal the cached balance
    assert ledger_balance(db, acct.id) == acct.points_balance == 100


def test_accrual_is_idempotent_per_order(db):
    w = make_world(db, earn_rate=1)
    c = _customer(db)
    o = _order(db, w)

    first = accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=o.id)
    replay = accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=o.id)

    assert first == replay == 150          # replay returns the already-earned total
    acct = _merchant_account(db, w, c.id)
    assert acct.points_balance == 150       # credited once, not twice
    assert acct.visit_count == 1            # visit not double-counted
    assert ledger_balance(db, acct.id) == 150


def test_keyless_accrual_not_deduped(db):
    """order_id=None can't be deduped — repeated keyless accrual is allowed (matches prior behaviour)."""
    w = make_world(db, earn_rate=1)
    c = _customer(db)
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("10.00"), order_id=None)
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("10.00"), order_id=None)
    acct = _merchant_account(db, w, c.id)
    # two keyless accruals both applied; balance still equals the ledger
    assert ledger_balance(db, acct.id) == acct.points_balance
    assert acct.visit_count == 2


def test_idempotency_key_rejects_duplicate_posting(db):
    w = make_world(db, earn_rate=1)
    c = _customer(db)
    accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id, amount=Decimal("100.00"), order_id=None)
    acct = _merchant_account(db, w, c.id)

    record_reward_txn(db, account=acct, txn_type=RewardTxnType.ADJUST.value, points=5,
                      reason="manual", idempotency_key="adj-001")
    db.flush()
    record_reward_txn(db, account=acct, txn_type=RewardTxnType.ADJUST.value, points=5,
                      reason="manual replay", idempotency_key="adj-001")
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
