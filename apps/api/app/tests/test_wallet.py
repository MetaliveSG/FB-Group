"""Stored-value wallet — ledger invariants + auto-reload via the PSP abstraction.

Guards: balance == SUM(ledger); replay-safe top-up; insufficient-balance blocks (no auto-reload);
auto-reload covers an order via the (mock) PSP; one wallet per (customer, loyalty-domain) + isolation.
The wallet is closed-loop per domain (FS Wallet / Tasty Wallet) — money never crosses.
"""
from decimal import Decimal

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError
from app.models.enums import WalletEntryType
from app.models.identity import Customer
from app.models.wallet import WalletLedger
from app.services import wallet
from app.services.payment_providers import MockPaymentProvider, get_payment_provider


def _customer(db, name="Wallet Cust"):
    c = Customer(full_name=name)
    db.add(c)
    db.flush()
    return c


def test_topup_and_spend_reconcile_to_ledger(db):
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    wallet.top_up(db, account=acct, amount=Decimal("50.00"), source_ref="pay_1")
    wallet.debit_for_order(db, account=acct, amount=Decimal("12.80"), order_id="ord_1")

    assert acct.balance == Decimal("37.20")
    assert wallet.ledger_balance(db, acct.id) == acct.balance
    assert wallet.verify_integrity(db, acct)["ok"]  # chain + reconciliation intact


def test_topup_is_idempotent(db):
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    wallet.top_up(db, account=acct, amount=Decimal("20.00"), idempotency_key="hitpay-evt-1")
    wallet.top_up(db, account=acct, amount=Decimal("20.00"), idempotency_key="hitpay-evt-1")  # replay

    assert acct.balance == Decimal("20.00")  # credited once
    assert wallet.ledger_balance(db, acct.id) == Decimal("20.00")


def test_debit_insufficient_without_autoreload_raises(db):
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    wallet.top_up(db, account=acct, amount=Decimal("5.00"))
    with pytest.raises(ConflictError) as ei:
        wallet.debit_for_order(db, account=acct, amount=Decimal("12.00"), order_id="ord_x")
    assert ei.value.code == "insufficient_balance"
    assert acct.balance == Decimal("5.00")  # untouched


def test_autoreload_covers_order_via_psp(db):
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    acct.auto_reload_enabled = True
    acct.saved_payment_token = "tok_mock_card"
    acct.auto_reload_amount = Decimal("20.00")
    wallet.top_up(db, account=acct, amount=Decimal("5.00"))
    db.flush()

    # Order $30, balance $5 → need $25 → 2 × $20 reload = +$40 → 45 → debit 30 → 15
    wallet.debit_for_order(db, account=acct, amount=Decimal("30.00"), order_id="ord_big")

    assert acct.balance == Decimal("15.00")
    assert wallet.ledger_balance(db, acct.id) == Decimal("15.00")
    types = [e.entry_type for e in acct.ledger]
    assert WalletEntryType.RELOAD.value in types
    assert WalletEntryType.SPEND.value in types
    assert wallet.verify_integrity(db, acct)["ok"]  # auto-reload keeps the chain intact


def test_ledger_is_hash_chained_and_verifies(db):
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    wallet.top_up(db, account=acct, amount=Decimal("20.00"))
    wallet.grant_bonus(db, account=acct, amount=Decimal("2.00"))
    wallet.debit_for_order(db, account=acct, amount=Decimal("7.00"), order_id="o1")

    rows = sorted(acct.ledger, key=lambda r: r.seq)
    assert [r.seq for r in rows] == [1, 2, 3]                 # monotonic per-account sequence
    assert rows[0].prev_hash == wallet.GENESIS_HASH           # chain anchored at genesis
    assert rows[1].prev_hash == rows[0].entry_hash            # each links to its predecessor
    assert rows[2].prev_hash == rows[1].entry_hash
    report = wallet.verify_integrity(db, acct)
    assert report["ok"] and report["entries"] == 3
    assert report["ledger_sum"] == report["balance"] == Decimal("15.00")


def test_tampering_with_a_posting_is_detected(db):
    """Non-repudiation: editing a committed ledger row breaks the hash chain → verify_integrity fails.
    (In Postgres the immutability trigger blocks the UPDATE outright; here we force it to prove detection.)"""
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    wallet.top_up(db, account=acct, amount=Decimal("20.00"))
    wallet.debit_for_order(db, account=acct, amount=Decimal("5.00"), order_id="o1")
    assert wallet.verify_integrity(db, acct)["ok"]

    # Forge: bump a historical amount (e.g. claim a bigger top-up) directly in the table.
    target = sorted(acct.ledger, key=lambda r: r.seq)[0]
    db.execute(update(WalletLedger).where(WalletLedger.id == target.id).values(amount=Decimal("200.00")))
    db.flush()
    db.expire_all()

    report = wallet.verify_integrity(db, acct)
    assert not report["ok"]                                    # tamper detected
    assert any("tampered" in e or "drift" in e for e in report["errors"])


def test_balance_cannot_go_negative_db_constraint(db):
    """Deposit-only backstop: the CHECK (balance >= 0) rejects a negative balance even if code is bypassed."""
    c = _customer(db)
    acct = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    acct.balance = Decimal("-1.00")
    db.add(acct)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_one_wallet_per_customer_per_domain_and_isolation(db):
    c = _customer(db)
    a1 = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    a1_again = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="FSG")
    a2 = wallet.get_or_create_account(db, customer_id=c.id, loyalty_domain_id="TASTY")

    assert a1.id == a1_again.id            # idempotent
    assert a1.id != a2.id                   # separate wallet per enterprise (FS vs Tasty)

    wallet.top_up(db, account=a1, amount=Decimal("40.00"))
    # money never crosses the domain — the other enterprise's wallet is unaffected
    assert a2.balance == Decimal("0.00")
    assert wallet.ledger_balance(db, a2.id) == Decimal("0.00")


def test_payment_provider_mock_is_default_and_pluggable(db):
    p = get_payment_provider()
    assert isinstance(p, MockPaymentProvider)
    session = p.create_payment(amount=Decimal("9.40"), currency="SGD", reference="ord_1")
    assert session.checkout_url and session.reference == "ord_1" and session.status == "pending"
    charge = p.charge_saved(token="tok", amount=Decimal("20.00"), currency="SGD", reference="reload:x")
    assert charge.ok and charge.status == "completed"
