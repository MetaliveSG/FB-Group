# POS MVP — proof of viability

Flow transcripts + screenshots + acceptance-criteria results. See BUGLOG.md for found/fixed defects.

## E2E run 1 (2026-06-05) — full flow PASS
Setup (bind Pepper Lunch @ TPY via QR) → PIN unlock (2580) → order (2× Beef Pepper Rice + 1× Chicken
Pepper Rice) → Charge $34.70 → pay CASH → receipt (Pepper Lunch Pte Ltd header, TOTAL $41.61, CASH +
mock ref, footer). 5 menu items loaded; zero page errors. Screens: 01_order.png, 02_receipt.png.
Acceptance covered: 1 (PIN login) · 2 (tap→pay, ~4 taps) · 4 (receipt w/ console header) · payments mock.
Pending UI: console PIN-mgmt + receipt-config screens (slice 6); diner/voucher redeem at the storefront POS (wired, e2e next).

## Slice 6 (2026-06-05) — console config UIs verified
- Settings → "Receipt header (POS)" card (company/UEN/address/phone/footer) — verified prefilled from config.
- Platform node drawer → "Set PIN" per node login (reset POS PIN at the console).
- Re-ran POS e2e after the receipt stall-dedup fix: PASS (02_receipt.png regenerated). Zero page errors.

## MVP acceptance — status
1. PIN login (set/reset at console) ✅   2. tap→pay ≤4 taps (cash/card/PayNow/NETS/PayWave mock) ✅
3. diner attach (phone) + voucher redeem at the storefront POS ✅ (reward-catalog redeem = diner in-app → voucher → cashier; staff can list a diner's vouchers)
4. receipt w/ console company header ✅   5. console transactions/report/redemptions ✅ (Reports/Orders + payments split)
6. tenant-scoped + suspend-aware + PDPA-consistent ✅ · tests green (276 backend + 58 frontend) · proof here.
Payments = MOCK (provider integration later phase, per spec). **POS MVP = viable.**

## Open-POS wiring (2026-06-06)
Repurposed the cosmetic `pos_enabled` module flag → "Staff POS" (Settings relabel). Org tree now carries
each storefront's tenant `pos_enabled`; the Platform directory shows an "Open POS" button beside "QR Menu"
on STOREFRONT rows when enabled (not on chains) → `/pos?bind={token}` auto-binds that outlet. Verified:
enabling Staff POS on Pepper Lunch surfaced Open POS on its 3 storefronts (screens/03_open_pos_button.png),
zero errors.

## Web/POS login segregation + readable per-storefront PINs + auto-team (2026-06-06/07)
**POS users are SEGREGATED from web logins** (`User.kind` = "web" | "pos", migration `x2y3userkind`).
A POS user is PIN-only: synthetic `@pos.local` email + locked password → can't web-login; a web user
can't PIN-login. **PINs are stored READABLY (owner choice — migration `y3z4pospin`):** the owner reveals
any operator's current PIN via an eye icon and can **set a chosen PIN** or auto-generate one; PINs are
**unique per storefront**. Creating a Storefront auto-provisions a **3-person team (1 manager + 2
cashiers)**. Owners self-serve via **Settings → "Staff & PINs (POS)"** (list with eye-reveal · Change PIN ·
add with optional chosen PIN · remove); the node drawer's web "Set PIN" was removed ("Logins" → "Web
logins"). Endpoints: `GET/POST /org/nodes/{id}/pos-staff` (create accepts an optional `pin`),
`POST …/{uid}/reset-pin` (body `{pin}` = chosen, or omit = auto), `DELETE …/{uid}`; pin-login takes
`outlet_id`. Backend: `test_pos_pin.py` (9, rewritten) + `test_pos_receipt.py` (3) green.
**Security note:** PINs readable at rest (low-risk 6-digit storefront credential) — KIV encrypt-at-rest.

**Proof — `segregation_proof.mjs` (live):**
- [1] storefront created → team of **3**, **3 unique 6-digit PINs**, outlet provisioned.
- [2] PIN-login at the bound outlet → **200**.
- [3] same PIN at a **different** storefront → **401** (per-storefront scope).
- [4] a `@pos.local` id at the web login → **422** (POS accounts can't web-login).
- [4b] list returns **readable PINs** (eye-reveal); **set chosen PIN 246813** → login with it **200**.
- [5] browser: bind storefront → PIN keypad → **order screen**, zero errors (screens/seg_01_pos_after_pin.png).

**Settings card (live, owner@pepperlunch.sg):** card shows the backfilled **3** operators; the **eye**
reveals each PIN; **Change PIN** sets a chosen value (or randomize); **Add operator** (optional chosen
PIN); zero errors. `seed_demo_merchants` backfills a 1+2 team per storefront (idempotent).
