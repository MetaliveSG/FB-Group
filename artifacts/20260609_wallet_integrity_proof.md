# Proof of Work — Wallet integrity + non-repudiation (2026-06-09)

Stored-value wallet (FS Wallet / Tasty Wallet) built **PSP-ready** so HitPay is a drop-in adapter.
Reviewed via `/my-architect` + `/my-dba`. Money/integrity change → dated evidence per the wrapup discipline.

## Integrity contract enforced
1. **Non-repudiable, tamper-evident ledger** — every `wallet_ledger` row is **hash-chained**: `seq`
   (per-account monotonic) + `prev_hash` + `entry_hash = SHA-256(canonical fields ‖ prev_hash)`. Any
   edit/insert/delete breaks the chain → `wallet.verify_integrity()` returns `ok=False`.
2. **Append-only / immutable** — code only INSERTs; **Postgres trigger `trg_wallet_ledger_immutable`
   blocks UPDATE/DELETE** (migration `c7d8wallet`). Hash-chain catches tampering on any DB.
3. **balance == SUM(ledger)** — cached `balance` rolled atomically per post; `verify_integrity` reconciles
   `balance == SUM == last.balance_after`.
4. **Non-negative** — `CHECK (balance >= 0)` + `CHECK (balance_after >= 0)` (deposit-only); debit guards first.
5. **Concurrency-safe** — `SELECT … FOR UPDATE` row-lock on the account before each post → no double-spend race.
6. **Idempotent** — unique `(wallet_account_id, idempotency_key)`; credits replay-safe.
7. **PSP seam** — `PaymentProvider` ABC + `MockPaymentProvider` + registry; auto-reload via `charge_saved`.
   HitPay = add `HitPayProvider` + `register_provider("hitpay", …)`, nothing else changes.

## Test proof
```
cd apps/api && .venv/bin/python -m pytest app/tests/test_wallet.py -q   → 9 passed
cd apps/api && .venv/bin/python -m pytest -q                            → 300 passed, 0 failed
cd apps/web && npm test                                                 → 63 passed (7 files)
```
Wallet tests (9): topup/spend reconcile · idempotent top-up · insufficient-balance blocked ·
**auto-reload covers an order via the PSP** · per-enterprise isolation · mock-PSP seam ·
**hash-chain verifies** · **tampering detected (non-repudiation)** · **non-negative DB CHECK**.

## Files
- `app/models/wallet.py` (WalletAccount, WalletLedger hash-chained) · `app/models/enums.py` (WalletEntryType)
- `app/services/wallet.py` (post/credit/top_up/debit_for_order/auto-reload/verify_integrity/summary)
- `app/services/payment_providers.py` (PSP abstraction + mock) · `alembic/versions/c7d8wallet_*.py`
- `app/services/rewards.py` + `app/schemas/rewards.py` (wallet alongside coins in `/me/loyalty`)
- `packages/api-client/src/index.ts` + `apps/web/.../rewards/page.tsx` (Wallet shown alongside Coins)
- `app/tests/test_wallet.py`

## Count deltas (reconcile at /my-wrapup)
- Backend tests **291 → 300** (50 files) · tables **43 → 45** (wallet_accounts, wallet_ledger) ·
  migrations **26 → 27** (head `c7d8wallet`) · endpoints unchanged (extended `/me/loyalty`, no new route).

## Status / next
Wallet is **Phase-2-ready, PSP-pluggable**. Order-ahead checkout will call `wallet.debit_for_order` /
`payment_providers.create_payment`. Remaining for live: HitPay adapter (on approval) + the `/me/wallet`
top-up routes + saved-card consent UI (build slices 2–3, `docs/payments-build-spec.md`).
