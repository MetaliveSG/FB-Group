# POS MVP — proof of viability

Flow transcripts + screenshots + acceptance-criteria results. See BUGLOG.md for found/fixed defects.

## E2E run 1 (2026-06-05) — full flow PASS
Setup (bind Pepper Lunch @ TPY via QR) → PIN unlock (2580) → order (2× Beef Pepper Rice + 1× Chicken
Pepper Rice) → Charge $34.70 → pay CASH → receipt (Pepper Lunch Pte Ltd header, TOTAL $41.61, CASH +
mock ref, footer). 5 menu items loaded; zero page errors. Screens: 01_order.png, 02_receipt.png.
Acceptance covered: 1 (PIN login) · 2 (tap→pay, ~4 taps) · 4 (receipt w/ console header) · payments mock.
Pending UI: console PIN-mgmt + receipt-config screens (slice 6); diner/voucher redeem at till (wired, e2e next).

## Slice 6 (2026-06-05) — console config UIs verified
- Settings → "Receipt header (POS)" card (company/UEN/address/phone/footer) — verified prefilled from config.
- Platform node drawer → "Set PIN" per node login (reset POS PIN at the console).
- Re-ran POS e2e after the receipt stall-dedup fix: PASS (02_receipt.png regenerated). Zero page errors.

## MVP acceptance — status
1. PIN login (set/reset at console) ✅   2. tap→pay ≤4 taps (cash/card/PayNow/NETS/PayWave mock) ✅
3. diner attach (phone) + voucher redeem at till ✅ (reward-catalog redeem = diner in-app → voucher → cashier; staff can list a diner's vouchers)
4. receipt w/ console company header ✅   5. console transactions/report/redemptions ✅ (Reports/Orders + payments split)
6. tenant-scoped + suspend-aware + PDPA-consistent ✅ · tests green (276 backend + 58 frontend) · proof here.
Payments = MOCK (provider integration later phase, per spec). **POS MVP = viable.**

## Open-POS wiring (2026-06-06)
Repurposed the cosmetic `pos_enabled` module flag → "Staff POS" (Settings relabel). Org tree now carries
each storefront's tenant `pos_enabled`; the Platform directory shows an "Open POS" button beside "QR Menu"
on STOREFRONT rows when enabled (not on chains) → `/pos?bind={token}` auto-binds that outlet. Verified:
enabling Staff POS on Pepper Lunch surfaced Open POS on its 3 storefronts (screens/03_open_pos_button.png),
zero errors.

## Web/POS login segregation + per-storefront PINs + auto-team (2026-06-06)
**POS users are now SEGREGATED from web logins** (`User.kind` = "web" | "pos", migration `x2y3userkind`).
A POS user is PIN-only: synthetic `@pos.local` email + locked password → can't web-login; a web user
can't PIN-login. PINs are bcrypt-hashed (one-way), **unique per storefront**, **revealed once** at
generate/reset (server-generated). Creating a Storefront auto-provisions a **5-person team (1 manager +
4 cashiers)** with one-time PINs. Owners self-serve via **Settings → "Staff & PINs (POS)"** (list / add /
reset-reveal / remove); the node drawer's web "Set PIN" was removed ("Logins" → "Web logins").
Endpoints: `GET/POST /org/nodes/{id}/pos-staff`, `POST …/{uid}/reset-pin`, `DELETE …/{uid}`; pin-login
now takes `outlet_id`. Backend: 10 tests in `test_pos_pin.py` (rewritten) + `test_pos_receipt.py` green.

**Proof — `segregation_proof.mjs` (live):**
- [1] storefront created → team of 5, **5 unique 6-digit PINs**, outlet provisioned.
- [2] PIN-login at the bound outlet → **200** (Cashier 1).
- [3] same PIN at a **different** storefront → **401** (per-storefront scope).
- [4] a `@pos.local` id at the web login → **422** (POS accounts can't web-login).
- [5] browser: bind till → PIN keypad → **order screen**, zero errors (screens/seg_01_pos_after_pin.png).

**Settings card (live, owner@pepperlunch.sg):** card shows the backfilled **5** operators; **Reset PIN**
reveals a fresh 6-digit PIN with a "shown once" banner; **Add operator** reveals a PIN (→ 6); zero errors.
`seed_demo_merchants` now backfills a POS team per storefront (idempotent; 6 seeded on the demo set).
