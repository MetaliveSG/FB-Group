# Payments — PSP · build spec · FSG wallet · uPOS integration (foodcourt pilot)

_Replaces the **mock** payment in CIP checkout with real money for the SG foodcourt pilot, plus the FSG
stored-value wallet and the uPOS side-integration. Plugs into the existing `checkout`/`record_sale()`
path. Critical-path #1 for the pilot (`docs/business/foodcourt-pilot-kit.md`). **Status: PLAN** (nothing built).
Consolidated 2026-06-12 from `payments-scope.md` + `payments-build-spec.md` + `wallet-scope.md` +
`upos-integration-spec.md` (originals removed; full text in git history). Verify exact HitPay API fields
against their current docs before coding. Wallet section ≠ legal advice._

## 1. Decisions
- **PSP — ✅ LOCKED: HitPay** (2026-06-09). Best **local e-wallet coverage** (PayNow, GrabPay,
  **ShopeePay**, Atome/BNPL — Stripe lacks ShopeePay) + **lower fees** + SG-native first-class PayNow +
  recurring billing (needed for auto-reload). Trade accepted: **hosted-checkout** UX (vs Stripe inline).
  *Stripe* = fallback only if inline in-webapp wallet UX or **Connect** per-stall settlement becomes the
  priority. **KPay parked** (terminal acquirer, no confirmed online web API; the counter lane is uPOS).
- **Merchant-of-record — ✅ LOCKED: FSG (single account)** — one HitPay account; top-ups + order-ahead
  funds land with FSG; FSG settles stalls off-platform for the pilot. No per-stall KYC → fastest; also
  de-risks the wallet's single-purpose status. **Per-stall split settlement = M2, deferred** — don't
  accidentally scope Connect now.
- **Wallet — ✅ LOCKED (2026-06-09): FSG-issued, CIP white-label rails, tenant-scoped** (§7). Universal
  cross-enterprise CIP wallet = deferred coalition; **money never crosses an enterprise, coins can** (M2).
- **Open (tune at build):** reload threshold + increment (default **< $5 → $20**), min/max balance,
  auto-reload opt-in default (recommend **off**, prompt after first manual top-up).

## 2. PSP choice — the comparison (kept for the record)
Both support all four headline methods (Apple Pay, Google Pay, PayNow, cards); the real axes were
**e-wallet coverage + fees (→ HitPay)** vs **inline UX + Connect (→ Stripe)**:

| | **Stripe** | **HitPay** (chosen) |
|---|---|---|
| Apple Pay + Google Pay | inline via **Express Checkout Element** (no redirect) | supported, on HitPay's **hosted checkout** |
| Render model | embeddable elements in our webapp | hosted checkout (redirect/embed) |
| PayNow | supported (SGD; QR, async webhook) | **first-class / native**, SG SME default |
| Cards + 3DS/SCA | yes, PSP-handled | yes |
| Local e-wallets | GrabPay, AliPay, WeChat Pay — **NO ShopeePay / Atome** | **GrabPay, ShopeePay, Atome (BNPL), "Later" options**, AliPay, WeChat Pay |
| Dev experience | best-in-class | good, simpler/SG-focused |
| Fees (SG, indicative) | ~3.4% + S$0.50 cards; PayNow lower | **lower** cards; PayNow cheap |
| Per-stall settlement | **Stripe Connect** (mature) | split options exist |

SG foodcourt diners pay with **PayNow + GrabPay + ShopeePay** every day → coverage decided it.

**How each method behaves (expectations):**
- **Apple Pay (web):** HTTPS on a real domain + a **domain-association file** at `/.well-known/…`;
  shows only on Apple/Safari. **Google Pay (web):** shows on Chrome/Android. Both are card-backed
  one-tap wallets.
- **Cards:** PSP-hosted elements only — raw card data never touches our server → **PCI SAQ-A**. 3DS by PSP.
- **PayNow is ASYNC:** show the QR, diner scans with their bank app, confirmation arrives **out-of-band
  via webhook** → checkout must handle **pending → paid**, never assume instant.

## 3. Payment architecture
**Backend (`apps/api/app/services/payments.py`):**
- `create_payment(order_id, amount, currency="SGD") -> {checkout_url, payment_ref}` → HitPay **Payment
  Request** (`amount`, `currency`, `reference_number=order_id`, `redirect_url`, `webhook`); returns the
  hosted-checkout `url` + request id. Diner pays on HitPay (any method).
- **Webhook** `POST /api/v1/payments/hitpay/webhook` → **verify HMAC** (HitPay salt over payload) ·
  **idempotent** by `payment_request_id` · on `status=completed` → mark `Payment` paid →
  **`record_sale()`** (Transaction + loyalty/CRM, the existing path) → advance the order.
  Replay-safe; log + 200 fast (HitPay retries on non-2xx).
- `refund_payment(payment)` → HitPay refund API → powers the **void flow** (`orders.void_order`) for real.

**Order-state machine:**
```
created → pending_payment → PAID (webhook) → [order-ahead] sent_to_stall → ready → collected
                          ↘ payment_failed/expired (retry/cancel)
PAID → voided → refunded            (supervisor void → HitPay refund)
```
- The **order-ahead lane** uses this. The **queue lane** does NOT (paid at uPOS; earns via the signed
  receipt-QR — §8). `sent_to_stall` = uPOS inbound injection if available, else the CIP order screen.

**Frontend (`apps/web`):**
- Checkout "Pay" → if wallet on + sufficient → **debit wallet (1 tap)**; else **HitPay hosted checkout**
  (or auto-reload then wallet). Pending→paid UX for PayNow (QR + "waiting" + expiry/timeout).
- Order-status + "Order #N ready" screen (ties into the fulfilment/KDS flow,
  `architecture-fulfilment-modes.md`).
- Wallet UI: balance, manual top-up (any method), auto-reload toggle + consent (off by default), history.

## 4. Data model (additive — migrations)
- **`Payment`** (extend): `provider="hitpay"`, `provider_ref` (payment_request_id), `method`
  (paynow/card/…), `status` (pending/paid/failed/refunded). Reuse the existing `Transaction` on the
  record_sale path.
- **`Order`**: `pickup_number` (per stall/day) — per the fulfilment-modes spec (the `hand_off` axis is
  already built).

## 5. Effort · build slices · Week-0
| Work | Est |
|---|---|
| HitPay account + PayNow activation + **KYC** (FSG) | lead time **days** — start Wk-0, runs parallel |
| Backend: payment service + Payment Request + webhook + wire to `record_sale` | **3–5 d** |
| Frontend: hosted-checkout handoff + PayNow pending state | **2–3 d** |
| Apple Pay domain verification + wallet config | **0.5–1 d** |
| Refund path for void flow | **1 d** |
| Testing: sandbox, 3DS, **PayNow async**, refunds, idempotent webhooks | **2–3 d** |
| **Total dev** | **~1.5–2 weeks** (+ KYC lead time in parallel) |

**Build slices (ship in order):**
1. **Pay-per-order via HitPay + webhook + order-state** → *the pilot critical path* (+10% measurable).
2. **Wallet ledger + manual top-up** (tenant-scoped) → in-app balance + 1-tap spend.
3. **Saved-card + auto-reload (< $5 → $20) + top-up bonus** → Phase-2 lock-in, **gated on the wallet
   legal one-pager** — don't block +10% on it.

**Week-0 checklist (FSG + CIP):** FSG HitPay merchant account + KYC + PayNow activation (lead time —
start now) · webhook URL allow-listed + HMAC salt shared + sandbox keys · recurring billing enabled
(auto-reload card-on-file) · stall→member-tree mapping (one storefront node per stall) · the 4 uPOS
capability questions (§8).

## 6. Gotchas / risks
- **PayNow async** → design pending→paid UX deliberately (QR, waiting, webhook confirm, expiry).
- **Apple Pay web** = domain-association file + HTTPS + real domain (PWA must be on a proper domain).
- **KYC / PayNow activation lead time can gate go-live** — start Week 0.
- **PCI:** PSP-hosted elements only; never a raw card form (stays SAQ-A).
- **Webhooks:** signature-verify + idempotent (PayNow + retries).
- **Fees vs margin:** ~2–3.4%/txn — factor into the +10% economics + coupon guardrails (Luckin CFO
  discipline).

## 7. The FSG wallet (closed-loop stored value + auto-reload)
_The Starbucks/Alipay model: a stored-value balance + auto-reload so the diner is never blocked.
Strategic role: **float + lower fees + lock-in (M5)** → compounds the +10%._

**Ownership + boundaries (locked 2026-06-09):**
- **FSG-issued / FSG-held** — top-ups land in FSG's HitPay account → FSG holds the float + owes the
  balance (FSG = the stored-value issuer). **CIP provides the ledger + app/UX + auto-reload tech.**
- **One branded wallet per enterprise** (FS Wallet, Tasty Wallet, …), spendable within that group only.
  **Scoped to the loyalty-domain ring (`loyalty_domain_id`)** — same boundary as coins, so wallet +
  coins share one account per customer per enterprise. (For FSG the group node carries both flags →
  loyalty-domain == settlement-boundary coincide; scoping to `loyalty_domain_id` is future-proof.)
- **Light/single-purpose holds while the enterprise = ONE settlement boundary** (true for the pilot).
  An enterprise spanning multiple settlement boundaries = multi-merchant stored value (heavier MAS) +
  cross-settlement (M2) — flag then.
- **Cross-enterprise = COINS ONLY.** Wallet **money never crosses an enterprise** (keeps it
  single-purpose/light; a universal cross-enterprise money wallet does not exist, by design). Coins can
  cross via the **coalition ring** — loyalty value, not stored money → no e-money licensing; only
  cross-enterprise coin redemption needs coalition clearing (M2, deferred) + the discipline *"never wire
  unverified earn to the coalition pool."* Layering: *within enterprise* = wallet (money) + domain
  coins; *cross-enterprise* = coalition coins only.
- **Closed-loop, deposit-only, no cash-out** → lightest stored-value treatment (not money transmission).

**Top-up:**
- **Manual** — any PSP method (PayNow, cards, GrabPay/ShopeePay, Apple/Google Pay).
- **Auto-reload (fixed increment when low), via saved card:**
  `if balance < THRESHOLD → off-session charge RELOAD_AMOUNT → credit wallet` (e.g. **< $5 → $20**).
  Needs a **tokenised card** (off-session); PayNow/e-wallets are on-session → manual only. **Explicit
  opt-in consent** (clear T&Cs). Fixed increment on purpose → fewer PSP charges + more float.
- **Top-up bonus** ("top up $50, get $5") — margin-friendly growth lever (Starbucks/Luckin play).

**Spend:** order-ahead checkout **debits the wallet** → one tap, no PSP round-trip per order (fast +
low fee). Insufficient + auto-reload on → reload fires first; off → prompt manual top-up.

**Build — on the existing ledger (don't buy; no turnkey SG F&B wallet exists).** A wallet = a ledger +
a top-up rail. Reuse the **loyalty posting-ledger pattern** (append-only, balance = SUM, idempotent,
domain-stamped) with currency instead of coins:
- **`WalletAccount`** `{id, customer_id, loyalty_domain_id, balance_cached, currency}`.
- **`WalletLedger`** (append-only) `{id, wallet_account_id, type ∈ {topup, spend, reload, bonus, refund,
  adjust}, amount, balance_after, source_ref, idempotency_key, created_at}`.
- **Operations** (all idempotent + tenant-scoped): `top_up(customer, tenant, amount, hitpay_ref)` ·
  `debit_for_order(order)` (auto-reload first if enabled) · `auto_reload(account)` (off-session charge
  via HitPay recurring billing) · `grant_bonus` · refund/void → `type=refund`.
- New pieces beyond reuse: top-up flow, debit-at-checkout, card vaulting + off-session charge, the
  auto-reload rule, balance + consent UI. *(Hardened ledger primitives — Formance/TigerBeetle — exist
  if ever needed at scale; overkill for the pilot.)*
- **Float/liability:** balance = FSG's liability (FSG's HitPay account holds the cash); segregate the
  float (no commingling), refund/dormancy policy, no cash-out. CIP surfaces the data; policy = FSG's.

**Regulatory (verify with a lawyer — cheap one-pager):** deposit-only + closed-loop + FSG-as-collector
≈ the light lane (likely **limited-purpose under the MAS Payment Services Act**, outside e-money
licensing). **Confirm the multi-stall point** (spend across independent stalls) — FSG-as-MoR is the
structural fix.

**Economics:** one PSP charge per **$20 reload** vs a fee on every $5 meal → big margin win at
foodcourt tickets; float (Starbucks holds ~US$1B+); standing balance + card-on-file = lock-in (M5).

**Phasing:** pilot ships **pass-through** payment first (prove +10% without regulatory lead time);
wallet is the **fast-follow lock-in amplifier** once the legal one-pager clears + saved-card is wired.

## 8. uPOS integration (the counter/queue lane — extractable as a handout for uPOS)
_All foodcourt stalls run uPOS (one vendor → one integration → all stalls). uPOS is **not replaced** —
small tweaks only. FSG (the paying uPOS customer) drives the request + timeline._

**Ask uPOS these 4 capability questions FIRST (Week 0):**
1. **Outbound:** webhook/API call on every completed sale to a configurable HTTPS endpoint?
2. **Receipt:** can the receipt template embed a **dynamic QR** (per-transaction URL/token)?
3. **Inbound:** an API to create/inject an order into a stall's queue (+ status callbacks)?
4. **Per item: effort, timeline, cost, and a sandbox?**

**Tweak 1 — Outbound transaction webhook ★ MUST-HAVE.** Fires on sale completed/paid → powers **100%
capture + the +10% baseline/measurement** + the receipt-QR match.
- HTTPS `POST` to a CIP URL (config per env); retry w/ backoff on non-2xx.
- Auth: `X-uPOS-Signature` = **HMAC-SHA256(body, shared_secret)** (CIP verifies). Idempotent by `txn_id`.
- Payload:
```json
{ "event":"sale.completed", "txn_id":"UPOS-...", "location_id":"court-01", "stall_id":"stall-07",
  "amount":12.80, "currency":"SGD", "payment_method":"paynow",
  "items":[{"name":"Chicken Rice","qty":1,"unit_price":4.50}],
  "receipt_no":"R-000123", "timestamp":"2026-06-09T12:30:05+08:00" }
```

**Tweak 2 — Signed receipt-QR ★ MUST-HAVE.** On receipt print, embed a QR = a CIP deep-link → webapp →
**verified coins** for that sale.
- Simplest + most secure (with #1): QR encodes only a reference → `https://app.<cip-domain>/r/{txn_id}`
  — CIP looks up the **webhook-recorded** sale (server-side truth = the bill amount).
- If #1 unavailable: QR must carry a **signed token** (HMAC/JWT of `{txn_id,stall_id,amount,ts}`) —
  **never plaintext amount** (forgeable). CIP enforces **one-time claim** per `txn_id`.

**Tweak 3 — Inbound order injection ☆ NICE-TO-HAVE (verify it's actually small).** CIP pushes paid
order-ahead orders into the stall's own uPOS queue → no double-handling:
```json
{ "stall_id":"stall-07", "external_order_id":"CIP-...", "order_type":"pickup", "paid":true,
  "amount":9.40, "pickup_number":"42",
  "items":[{"name":"Kaya Toast Set","qty":1,"modifiers":["less sugar"]}] }
```
Status callbacks (accepted/preparing/**ready**) via the #1 webhook → drives the diner "ready" push.
**Fallback if not small:** a CIP order screen at the stall — the pilot is never blocked on #3.

**Security & compliance:** HTTPS everywhere; HMAC shared secret per direction, rotate-able;
**no customer PII to uPOS** (CIP holds identity; uPOS deals only in txn/order data — PDPA-clean);
idempotency on `txn_id`/`external_order_id`; one-time QR claim.

**What CIP needs from uPOS to start:** confirmation of #1–#3 + cost/timeline; sandbox + shared secret +
endpoint allow-listing; the `location_id`/`stall_id` scheme so CIP maps stalls to the member-tree.
