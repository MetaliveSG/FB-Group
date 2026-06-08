"""Stored-value wallet service — append-only ledger + auto-reload, on the coin-ledger pattern.

Closed-loop, deposit-only, scoped to a loyalty domain (the enterprise ring: FS Wallet / Tasty Wallet).
`WalletAccount.balance` is a cache that always equals SUM(WalletLedger.amount) — every mutation goes
through `_post`. Top-ups are replay-safe by `idempotency_key`. Order debit never blocks when auto-reload is
on (charges the saved card via the PSP abstraction). Money never crosses the domain — that invariant lives
in the call sites (they always pass the order's own loyalty_domain). See docs/wallet-scope.md."""
from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.money import money
from app.db.base import utcnow
from app.models.enums import WalletEntryType
from app.models.wallet import WalletAccount, WalletLedger
from app.services.payment_providers import get_payment_provider

ZERO = Decimal("0.00")
GENESIS_HASH = "0" * 64  # prev_hash of the first posting in an account's chain


def _entry_hash(
    *, account_id: str, seq: int, entry_type: str, amount: Decimal, balance_after: Decimal,
    source_ref: str | None, created_at: datetime, prev_hash: str,
) -> str:
    """Deterministic SHA-256 over the posting's canonical fields ‖ prev_hash — the tamper-evident link."""
    canonical = "|".join([
        account_id, str(seq), entry_type, str(money(amount)), str(money(balance_after)),
        source_ref or "", created_at.isoformat(), prev_hash,
    ])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_or_create_account(
    db: Session, *, customer_id: str, loyalty_domain_id: str, currency: str = "SGD"
) -> WalletAccount:
    """One wallet per (customer, enterprise/loyalty-domain). Idempotent."""
    acct = db.scalar(
        select(WalletAccount).where(
            WalletAccount.customer_id == customer_id,
            WalletAccount.loyalty_domain_id == loyalty_domain_id,
        )
    )
    if acct is None:
        acct = WalletAccount(
            customer_id=customer_id, loyalty_domain_id=loyalty_domain_id, currency=currency
        )
        db.add(acct)
        db.flush()
    return acct


def summary(db: Session, *, customer_id: str, loyalty_domain_id: str) -> dict:
    """Read-only wallet view for the customer app (no side-effect create). Zero if no wallet yet."""
    acct = db.scalar(
        select(WalletAccount).where(
            WalletAccount.customer_id == customer_id,
            WalletAccount.loyalty_domain_id == loyalty_domain_id,
        )
    )
    if acct is None:
        return {"balance": ZERO, "currency": "SGD", "auto_reload_enabled": False}
    return {
        "balance": money(acct.balance), "currency": acct.currency,
        "auto_reload_enabled": bool(acct.auto_reload_enabled),
    }


def ledger_balance(db: Session, account_id: str) -> Decimal:
    """Source-of-truth balance = SUM(ledger). The cached `balance` must always equal this."""
    total = db.scalar(
        select(func.coalesce(func.sum(WalletLedger.amount), 0)).where(
            WalletLedger.wallet_account_id == account_id
        )
    )
    return money(total or 0)


def _post(
    db: Session, *, account: WalletAccount, entry_type: str, amount: Decimal,
    source_ref: str | None = None, idempotency_key: str | None = None, reason: str = "",
) -> WalletLedger:
    """Append one signed posting (+credit / -debit), extend the hash chain, and roll the cached balance.

    Concurrency-safe: takes a row lock on the account (`FOR UPDATE` on Postgres; no-op on SQLite) so two
    concurrent posts can't read the same balance/seq and double-spend. The ledger is the source of truth."""
    # Serialize per-account: lock the row before reading the tail of the chain.
    db.execute(select(WalletAccount.id).where(WalletAccount.id == account.id).with_for_update()).first()

    last = db.scalar(
        select(WalletLedger)
        .where(WalletLedger.wallet_account_id == account.id)
        .order_by(WalletLedger.seq.desc())
        .limit(1)
    )
    seq = (last.seq + 1) if last else 1
    prev_hash = last.entry_hash if last else GENESIS_HASH

    amount = money(amount)
    new_balance = money(account.balance + amount)
    created = utcnow()
    entry_hash = _entry_hash(
        account_id=account.id, seq=seq, entry_type=entry_type, amount=amount,
        balance_after=new_balance, source_ref=source_ref, created_at=created, prev_hash=prev_hash,
    )
    entry = WalletLedger(
        wallet_account_id=account.id, seq=seq, entry_type=entry_type, amount=amount,
        balance_after=new_balance, source_ref=source_ref, idempotency_key=idempotency_key, reason=reason,
        prev_hash=prev_hash, entry_hash=entry_hash, created_at=created,
    )
    db.add(entry)
    account.balance = new_balance
    db.flush()
    return entry


def _credit(
    db: Session, *, account: WalletAccount, entry_type: str, amount: Decimal,
    source_ref: str | None = None, idempotency_key: str | None = None, reason: str = "",
) -> WalletLedger:
    """Credit (positive). Replay-safe: a reused idempotency_key returns the existing entry, no double-credit."""
    amount = money(amount)
    if amount <= ZERO:
        raise ConflictError("Credit amount must be positive", code="bad_amount")
    if idempotency_key:
        existing = db.scalar(
            select(WalletLedger).where(
                WalletLedger.wallet_account_id == account.id,
                WalletLedger.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing
    return _post(db, account=account, entry_type=entry_type, amount=amount,
                 source_ref=source_ref, idempotency_key=idempotency_key, reason=reason)


def top_up(
    db: Session, *, account: WalletAccount, amount: Decimal, source_ref: str | None = None,
    idempotency_key: str | None = None, reason: str = "top-up",
) -> WalletLedger:
    """Manual top-up (any PSP method). Call after the PSP confirms the payment (webhook)."""
    return _credit(db, account=account, entry_type=WalletEntryType.TOPUP.value, amount=amount,
                   source_ref=source_ref, idempotency_key=idempotency_key, reason=reason)


def grant_bonus(db: Session, *, account: WalletAccount, amount: Decimal, reason: str = "top-up bonus") -> WalletLedger:
    return _credit(db, account=account, entry_type=WalletEntryType.BONUS.value, amount=amount, reason=reason)


def refund(db: Session, *, account: WalletAccount, amount: Decimal, source_ref: str | None = None,
           reason: str = "refund") -> WalletLedger:
    return _credit(db, account=account, entry_type=WalletEntryType.REFUND.value, amount=amount,
                   source_ref=source_ref, reason=reason)


def _auto_reload_to_cover(db: Session, *, account: WalletAccount, target: Decimal) -> WalletLedger | None:
    """Charge the saved card (off-session, via the PSP) by whole `auto_reload_amount` increments until the
    balance covers `target`. One charge for the full needed amount. Returns the RELOAD posting (or None)."""
    increment = money(account.auto_reload_amount)
    if increment <= ZERO:
        return None
    needed = money(target - account.balance)
    if needed <= ZERO:
        return None
    n = int((needed / increment).quantize(Decimal("1"), rounding=ROUND_CEILING))
    charge = money(increment * n)
    result = get_payment_provider().charge_saved(
        token=account.saved_payment_token, amount=charge, currency=account.currency,
        reference=f"reload:{account.id}",
    )
    if not result.ok:
        raise ConflictError("Auto-reload charge failed", code="reload_failed")
    return _credit(db, account=account, entry_type=WalletEntryType.RELOAD.value, amount=charge,
                   source_ref=result.provider_ref, reason="auto-reload")


def debit_for_order(
    db: Session, *, account: WalletAccount, amount: Decimal, order_id: str | None = None,
    idempotency_key: str | None = None,
) -> WalletLedger:
    """Pay an order from the wallet (one tap, no per-order PSP fee). If short and auto-reload is on with a
    saved card, top up via the PSP first so the diner is never blocked; otherwise raise insufficient_balance."""
    amount = money(amount)
    if amount <= ZERO:
        raise ConflictError("Debit amount must be positive", code="bad_amount")
    if account.balance < amount:
        if account.auto_reload_enabled and account.saved_payment_token:
            _auto_reload_to_cover(db, account=account, target=amount)
        if account.balance < amount:
            raise ConflictError("Insufficient wallet balance", code="insufficient_balance")
    return _post(db, account=account, entry_type=WalletEntryType.SPEND.value, amount=-amount,
                 source_ref=order_id, idempotency_key=idempotency_key, reason="order")


def verify_integrity(db: Session, account: WalletAccount) -> dict:
    """Reconcile + validate the non-repudiable chain for one wallet. Returns a report:
    `{ok, errors, entries, ledger_sum, balance}`. `ok` is True only when (1) the hash chain is intact
    (each row's recomputed hash matches + links to its predecessor), (2) `balance_after` runs consistently,
    and (3) the cached `balance` equals SUM(ledger) equals the last `balance_after`. Any tamper → ok=False."""
    rows = db.scalars(
        select(WalletLedger)
        .where(WalletLedger.wallet_account_id == account.id)
        .order_by(WalletLedger.seq.asc())
    ).all()

    errors: list[str] = []
    prev_hash = GENESIS_HASH
    running = ZERO
    for i, r in enumerate(rows, start=1):
        if r.seq != i:
            errors.append(f"seq gap/reorder at row {i}: seq={r.seq}")
        if r.prev_hash != prev_hash:
            errors.append(f"broken chain link at seq {r.seq}")
        recomputed = _entry_hash(
            account_id=r.wallet_account_id, seq=r.seq, entry_type=r.entry_type, amount=r.amount,
            balance_after=r.balance_after, source_ref=r.source_ref, created_at=r.created_at,
            prev_hash=r.prev_hash,
        )
        if recomputed != r.entry_hash:
            errors.append(f"tampered row at seq {r.seq} (hash mismatch)")
        running = money(running + r.amount)
        if money(r.balance_after) != running:
            errors.append(f"balance_after drift at seq {r.seq}: {r.balance_after} != {running}")
        prev_hash = r.entry_hash

    ledger_sum = money(running)
    if money(account.balance) != ledger_sum:
        errors.append(f"cached balance {account.balance} != ledger sum {ledger_sum}")

    return {
        "ok": not errors, "errors": errors, "entries": len(rows),
        "ledger_sum": ledger_sum, "balance": money(account.balance),
    }
