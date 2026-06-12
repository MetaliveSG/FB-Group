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

**Build slices — RE-SEQUENCED 2026-06-12 (FSG roadmap change, see `docs/decisions.md`):
loyalty/CRM rollout comes FIRST and is the new critical path; ordering moves last.**
1. **Loyalty + CRM capture at the EXISTING uPOS counters** — the §8 seam (outbound webhook +
   signed receipt-QR) is now the *critical path*, not a nice-to-have: diner pays at the counter as
   today, scans the receipt QR, earns coins, lands in CRM. Zero stall-operations change.
2. **Wallet / stored-card as a TENDER at the existing counters** — wallet ledger + manual top-up
   (tenant-scoped), plus a pay-at-counter design (NEW, to spec: diner presents a wallet QR /
   cashier charges via uPOS tender integration). Auto-reload + top-up bonus follow, gated on the
   wallet legal one-pager.
3. **Online ordering (order-ahead)** — pay-per-order via HitPay hosted checkout + webhook +
   order-state machine (§3) — formerly slice 1, now lands on top of an active loyalty base.

**Week-0 checklist (FSG + CIP):** FSG HitPay merchant account + KYC + PayNow activation (lead time —
start now) · webhook URL allow-listed + HMAC salt shared + sandbox keys · recurring billing enabled
(auto-reload card-on-file) · stall→member-tree mapping (one storefront node per stall) · the 6 uPOS
capability questions (§8 — Q1 webhook + Q5 scan-at-tender gate phase ①).

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

## 7b. Vouchers + Wallet at the existing counter — the scan-at-tender rail (LOCKED 2026-06-12)
_How a diner redeems a voucher (phase ①) or pays from the FS Wallet (phase ②) at the uPOS counter.
**The LOCKED flow is CUSTOMER-PRESENTED:** cashier bills in uPOS → diner shows a one-time CIP QR →
**cashier scans it → uPOS calls CIP → deducts → shows the balance due.** The diner NEVER keys the bill
amount — the till stays the single source of truth. ONE uPOS integration (scan-a-CIP-code at tender)
serves BOTH value types: a voucher token redeems a voucher; a wallet token charges the wallet; the
same rail later takes both in one scan (voucher + wallet remainder)._

**The worked example (the spec's north star):** new diner orders 2 kopi; cashier bills **$3** in uPOS;
diner scans the counter standee QR → registers (OTP + consent, **<60s, in-queue**) → welcome pack
5×$2 lands, voucher #1 unlocked → phone shows the **voucher QR** → cashier scans → uPOS deducts $2 →
**uPOS shows $1 balance** → diner pays $1 (cash/PayNow) → CIP marks voucher #1 USED, **#2 unlocks**,
**300 coins** granted (provisional → confirmed on the webhook match, which also attaches the 2× kopi
line items to the new customer profile).

**CAPTURE REQUIREMENT (LOCKED 2026-06-12, register row):** CIP must capture **WHAT items were sold,
WHERE (stall), and HOW MUCH** — for every counter sale, whatever the tender. Item-level data only
exists in uPOS (the till owns the basket), so the **§8 outbound webhook (payload includes `items[]`,
`stall_id`, `amount`) is NON-NEGOTIABLE for phase ① and ② alike** — no wallet option replaces it. The
wallet option choice below only sets the **match quality** between the payment and that webhook txn:
A/C link exactly by `txn_id` at charge time; B links fuzzily (stall+amount+time, tightened by any
receipt-QR scan), then inherits the txn's `items[]` once matched.

### The rail (LOCKED — the customer-presented model; was "Option A")
The webapp shows a **short-lived, single-use CIP code** (QR/barcode; server-issued; TTL ~90s; ONE
outstanding code per customer; encodes a token, never a value). At tender time the cashier **scans it
with the existing uPOS scanner**; uPOS calls **`POST /tender/scan {token, bill_amount, stall_id,
txn_id, items[]?}`** (HMAC-signed, same secret rail as §8); CIP resolves the token:
- **Voucher token** → validate rules (single-use · window · min-spend vs `bill_amount` · per-period
  cap) → redeem → return `{approved, deduct: 2.00}` → **uPOS applies it (discount or split-tender —
  whichever uPOS supports) and shows the balance due**.
- **Wallet token** (phase ②) → balance check (auto-reload if enabled) → debit → return
  `{approved, deduct: full or partial}` — same call, same screen.
- Later: one scan can return **voucher + wallet remainder** combined.
Response target **< 2s**; on timeout uPOS retries (idempotent by `txn_id`) or the cashier falls back
to normal tender (the diner's voucher stays unredeemed — never half-burned).

### Fallback ONLY if uPOS cannot scan-at-tender (Week-0 Q5 = no)
Manual two-step: cashier keys the uPOS discount + verifies the diner's live-clock redemption screen
(merchant-presented, glance-verified). Demoted to contingency 2026-06-12 — the diner-keys-amount
variant is **SUPERSEDED** (the till must own the bill; see `docs/decisions.md`). If Q5 = no, this
fallback runs the pilot while FSG presses uPOS for the scan rail.

### Engine (one rail, both value types — reuses the §7 ledger, additive)
- **Token service:** server-issued single-use code (TTL ~90s, ONE outstanding per customer), typed
  `voucher:{voucher_id}` or `wallet:{account_id}` — the QR carries a token, never a value.
- **`tender_intents`** `{id, customer_id, kind voucher|wallet, ref_id, stall_node_id, bill_amount,
  deduct_amount, status approved→matched|reversed, txn_id, created_at}` — every scan-approval is an
  intent; wallet debits post `WalletLedger type=spend, source_ref=intent_id`; voucher redemptions go
  through the EXISTING voucher core (`vouchers.redeem`, R39 — single-use · window · **min-spend
  validated against the uPOS `bill_amount`** · per-period cap). All **idempotent by `txn_id`** (uPOS
  retries must never double-redeem/debit).
- **Sequential unlock (welcome pack):** voucher N's redemption unlocks N+1 (`unlocks_next` on the
  grant) — small voucher-core extension; caps burn at one voucher per visit and manufactures the
  return visit.
- **Insufficient wallet balance** → auto-reload if enabled (§7), else decline with `top_up_required`
  (the webapp prompts; the cashier just sees "declined — other tender").
- **Earn (provisional → verified):** coins grant provisionally at approval (instant gratification in
  the webapp), **confirmed when the §8 webhook txn matches by `txn_id`** — the earn is never wired to
  self-reported data; no-double-earn vs the receipt-QR claim is deduped by the same `txn_id`.
- **Limits (consumer-protection + PSA light-touch):** per-txn cap (default S$100) · daily wallet-spend
  cap (default S$200) · earn rate + coin value = **tenant CONFIG, not constants** (pilot setting:
  100 coins/$1 gross bill, 100 coins = $1 food-only face — COGS-backed, see §Economics in §7).
- **Void/refund:** supervisor void at uPOS → reversal keyed to the intent/txn — voucher returns to
  issued, wallet gets `type=refund`, coins claw back. Same idempotency rail.

### Reconciliation (the FSG finance deliverable)
Every approval carries the uPOS `txn_id`, so matching is **exact**: webhook txns ↔ tender intents,
with `items[]` attaching to the customer profile (the item-level capture requirement) and **voucher
deductions as their own recon column** — the voucher value is funded by the FSG campaign/loyalty
budget, never by the stall (stalls are made whole in FSG's internal settlement; they must never feel
they personally fund the promo). Exceptions surface daily: approvals with no webhook txn, txns with
double deductions, provisional earns >24h unconfirmed.

### Risks
- **uPOS dependency is now phase-① critical path** (the scan-at-tender rail gates vouchers, not just
  wallet) — mitigated by the manual fallback above + FSG being the paying uPOS customer.
- **Connectivity:** the scan call needs uPOS online (<2s target) — on timeout, retry or normal tender;
  the diner's voucher is never half-burned (server state only flips on approval).
- **In-queue registration must fit <60s** — OTP autofill, one consent tap, voucher QR auto-shown;
  every extra screen costs conversions and queue goodwill.
- **No PII to uPOS** (PDPA): tokens carry refs only — identity stays in CIP.

### Effort
CIP-side ≈ **5–7 d** (token service + `/tender/scan` + `tender_intents` + sequential unlock + recon
report + the <60s registration polish). uPOS-side = their estimate for scan-at-tender (Week-0 Q5) —
the SAME integration later serves wallet (phase ②) with zero additional uPOS work.

## 8. uPOS integration (the counter/queue lane — extractable as a handout for uPOS)
_All foodcourt stalls run uPOS (one vendor → one integration → all stalls). uPOS is **not replaced** —
small tweaks only. FSG (the paying uPOS customer) drives the request + timeline._

**Ask uPOS these 6 capability questions FIRST (Week 0):**
1. **Outbound:** webhook/API call on every completed sale to a configurable HTTPS endpoint?
2. **Receipt:** can the receipt template embed a **dynamic QR** (per-transaction URL/token)?
3. **Inbound:** an API to create/inject an order into a stall's queue (+ status callbacks)?
4. **Custom tender:** can a named tender type ("FS Wallet") be added at config level (no integration)?
5. **Scan-at-tender (gates §7b — now PHASE-① critical path):** at tender time, can uPOS scan a
   QR/barcode and call an external HTTPS API, applying the returned deduction (discount or split
   tender) and showing the balance due?
6. **Per item: effort, timeline, cost, and a sandbox?**

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
