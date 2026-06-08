# uPOS × CIP — Integration Spec (foodcourt pilot)

_For **FSG** to hand to **uPOS**. Context: all foodcourt stalls run uPOS (one unit/stall, **one vendor → one
integration → all stalls**). CIP is the customer-facing **webapp** (no app install). uPOS is **not replaced** —
**small tweaks only.** Two customer lanes: **order-ahead** (non-queue) + **scan signed receipt-QR** (queue).
Pairs with `docs/foodcourt-pilot-kit.md` + `docs/architecture-fulfilment-modes.md`._

## Ask uPOS these 4 capability questions FIRST (Week 0)
1. **Outbound:** can uPOS fire a **webhook / API call on every completed sale** to a configurable HTTPS endpoint?
2. **Receipt:** can the **receipt template embed a dynamic QR** (a per-transaction URL/token)?
3. **Inbound:** is there an **API to create/inject an order** into a stall's queue (+ status callbacks)?
4. **Per item: effort, timeline, cost, and a sandbox/test environment?**

## The three tweaks (priority order)

### 1 — Outbound transaction webhook  ★ MUST-HAVE (high payoff, small for a cloud POS)
Fires on **sale completed/paid**. Powers **100% capture + the +10% baseline/measurement** and the receipt-QR match.
- **Transport:** HTTPS `POST` to a CIP URL (config per environment); retry w/ backoff on non-2xx.
- **Auth:** `X-uPOS-Signature` = **HMAC-SHA256(body, shared_secret)** (CIP verifies).
- **Idempotency:** unique `txn_id`; CIP dedupes retries.
- **Payload:**
```json
{ "event":"sale.completed", "txn_id":"UPOS-...", "location_id":"court-01", "stall_id":"stall-07",
  "amount":12.80, "currency":"SGD", "payment_method":"paynow",
  "items":[{"name":"Chicken Rice","qty":1,"unit_price":4.50}],
  "receipt_no":"R-000123", "timestamp":"2026-06-09T12:30:05+08:00" }
```

### 2 — Signed receipt-QR  ★ MUST-HAVE (small)
On receipt print, embed a QR = a CIP deep-link the diner scans → webapp → **verified coins** for that sale.
- **Simplest + most secure (with #1):** QR encodes only a reference →
  `https://app.<cip-domain>/r/{txn_id}` — CIP looks up the **webhook-recorded** sale (server-side truth =
  the bill amount). Minimal data in the QR, nothing forgeable.
- **If #1 isn't available:** QR must carry a **signed token** (HMAC/JWT of `{txn_id,stall_id,amount,ts}`,
  shared secret) — **never plaintext amount** (forgeable).
- CIP enforces **one-time claim** per `txn_id`.

### 3 — Inbound order injection  ☆ NICE-TO-HAVE (verify it's *small* — may not be)
Lets CIP push paid order-ahead orders **into the stall's own uPOS queue** → no separate order screen, no
double-handling. If not small → fall back to a CIP **order screen** at the stall (see pilot kit §1).
- **CIP → uPOS:** `POST create order`
```json
{ "stall_id":"stall-07", "external_order_id":"CIP-...", "order_type":"pickup", "paid":true,
  "amount":9.40, "pickup_number":"42",
  "items":[{"name":"Kaya Toast Set","qty":1,"modifiers":["less sugar"]}] }
```
- **Status callbacks** (accepted / preparing / **ready**) via the #1 webhook → drives the diner "ready" push.

## Security & compliance
- HTTPS everywhere; **HMAC shared secret** per direction; rotate-able.
- **No customer PII to uPOS** — CIP holds identity; uPOS deals only in txn/order data. (PDPA-clean.)
- Idempotency on `txn_id` / `external_order_id`; one-time QR claim.

## What CIP needs from uPOS to start
- Confirmation of #1–#3 (the 4 questions) + **cost/timeline** per item.
- **Sandbox** + a **shared secret** + endpoint allow-listing.
- The `location_id` / `stall_id` scheme so CIP maps to the member-tree (one storefront node per stall).

## Priority / fallback (so the pilot is never blocked)
- **#1 webhook + #2 signed receipt-QR = the must-haves** (measurement + queue-lane earn). Both small.
- **#3 inbound injection = upgrade**; if not small, order-ahead fulfilment uses a CIP order screen — pilot still runs.
- FSG (the paying uPOS customer) drives the request + timeline.
