# Payments — build spec (first slice: HitPay + order-ahead + wallet)

_Engineering spec for the foodcourt pilot's **order-ahead** payment + the FSG wallet. Decisions locked:
**PSP = HitPay** · **merchant-of-record = FSG (single account)** · **wallet = FSG-issued, CIP white-label,
tenant-scoped** (`docs/wallet-scope.md`). Plugs into the existing `checkout`/`record_sale()` path. Scopes:
`docs/payments-scope.md`, `docs/architecture-fulfilment-modes.md`. Verify exact HitPay API fields against
their current docs before coding. Status: PLAN._

## A. Locked decisions
- **PSP: HitPay** (hosted checkout; PayNow + cards + GrabPay/ShopeePay + Apple/Google Pay; recurring billing for auto-reload).
- **Merchant-of-record: FSG** — one HitPay account; top-ups + order-ahead funds land with FSG; FSG settles stalls (off-platform for pilot). Per-stall split = M2, deferred.
- **Wallet: FSG-issued, CIP rails, tenant-scoped.** Universal CIP wallet = deferred coalition.

## B. Payment service (backend `apps/api/app/services/payments.py`)
- `create_payment(order_id, amount, currency="SGD") -> {checkout_url, payment_ref}`
  → HitPay **Payment Request** (`amount`, `currency`, `reference_number=order_id`, `redirect_url`,
  `webhook`); returns hosted-checkout `url` + request id. Diner pays on HitPay (any method).
- **Webhook** `POST /api/v1/payments/hitpay/webhook`
  → **verify HMAC** (HitPay salt over the payload) · **idempotent** by `payment_request_id` ·
  on `status=completed` → mark `Payment` paid → **`record_sale()`** (Transaction + loyalty/CRM) → advance order.
  Reject/replay-safe; log + 200 fast (HitPay retries on non-2xx).
- `refund_payment(payment)` → HitPay refund API → for the **void flow** (`orders.void_order`).
- **PayNow is async:** order sits `pending_payment` until the webhook; UX shows the HitPay PayNow QR + "waiting".

## C. Order-state machine
```
created → pending_payment → PAID (webhook) → [order-ahead] sent_to_stall → ready → collected
                          ↘ payment_failed/expired (retry/cancel)
PAID → voided → refunded            (supervisor void → HitPay refund)
```
- **Order-ahead lane** uses this. **Queue lane** does NOT (paid at uPOS; earns via signed receipt-QR — separate flow).
- `sent_to_stall` = uPOS **inbound injection** if available, else the CIP **order screen** (`docs/foodcourt-pilot-kit.md`).

## D. Data model (additive — migrations)
- **`Payment`** (extend): `provider="hitpay"`, `provider_ref` (payment_request_id), `method` (paynow/card/…),
  `status` (pending/paid/failed/refunded). Reuse existing `Transaction` on the record_sale path.
- **`Order`**: `fulfilment_type` (default `dine_in`; pilot stalls = `pickup`) + `pickup_number` (per stall/day) — per fulfilment-modes spec.

## E. Wallet (FSG-scoped) — build on the existing ledger pattern
Reuse the loyalty posting-ledger shape (append-only, balance = SUM, idempotent, domain-stamped):
- **`WalletAccount`** `{id, customer_id, loyalty_domain_id (the enterprise ring — FS Wallet / Tasty Wallet),
  balance_cached, currency}`. Scoped to the **loyalty domain** (same boundary as coins; for the FSG pilot the
  group node carries both flags so it == the settlement boundary). One branded wallet per enterprise.
- **`WalletLedger`** (append-only) `{id, wallet_account_id, type, amount, balance_after, source_ref, idempotency_key, created_at}`
  where `type ∈ {topup, spend, reload, bonus, refund, adjust}`.
- **Operations:**
  - `top_up(customer, tenant, amount, hitpay_ref)` → credit (manual; any HitPay method).
  - `debit_for_order(order)` → `if balance < amount and auto_reload_on → auto_reload() first`, then debit.
  - `auto_reload(account)` → `if balance < THRESHOLD ($5) → HitPay off-session charge RELOAD ($20)` via the
    **saved card token** (HitPay recurring billing) → credit `type=reload`. Requires card-on-file + consent.
  - `grant_bonus` (e.g. top-up $50 → +$5) → credit `type=bonus`.
  - Refund/void → `type=refund`. All **idempotent** + **tenant-scoped**.
- **Float/liability:** balance = FSG's liability (FSG's HitPay account holds the cash). Safeguarding/refund/
  dormancy = FSG policy (CIP surfaces the data).

## F. Frontend (`apps/web`)
- Checkout: "Pay" → if wallet on + sufficient → **debit wallet (1 tap)**; else **HitPay hosted checkout**
  (or auto-reload then wallet). Pending→paid state for PayNow. Order-status + "Order #N ready" screen.
- Wallet UI: balance, **manual top-up** (any method), **auto-reload toggle + consent** (off by default), history.

## G. Week-0 setup (FSG + CIP)
- [ ] **FSG HitPay merchant account** + **KYC** + **PayNow activation** (lead time — start now).
- [ ] Webhook URL allow-listed + **HMAC salt** shared; **sandbox** keys.
- [ ] **Recurring billing** enabled (needed for auto-reload card-on-file).
- [ ] `tenant_id`/stall mapping to the member-tree (one storefront node per stall).

## H. Build slices (ship in order)
1. **Pay-per-order via HitPay + webhook + order-state** → *the pilot critical path* (order-ahead works; +10% measurable).
2. **Wallet ledger + manual top-up** (tenant-scoped) → in-app balance + 1-tap spend.
3. **Saved-card + auto-reload (< $5 → $20) + top-up bonus** → *Phase-2 lock-in* (after the wallet legal one-pager).

**Critical path = slice 1** (real HitPay payment). Slices 2–3 are the wallet/lock-in, gated on the legal one-pager — don't block +10% on them.
