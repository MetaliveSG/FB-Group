# POS MVP — spec & build plan (started 2026-06-05)

A staff-facing Point-of-Sale layer for an outlet/stall, on top of the existing order/payment/loyalty
/voucher engine. **Payment provider integration is a LATER phase — all payments are mock/simulated now**
(cash recorded; card/PayNow simulated success like the web app checkout).

## Goal (user spec, verbatim intent)
- POS MVP layer for an **outlet / stall**.
- Staff log in with an **easy PIN** (resettable at the web console).
- **Easy order system** (`/my-uiux` design): **minimum steps** from first tap → checkout → pay
  **cash / credit card / PayNow** (mock, as in the web-app ordering).
- **Print receipt** with stall/outlet info + **company header** (configured at the web console).
- **Redeem rewards / vouchers** at the POS.
- **Web console**: view transactions / reports / redemptions.
- **Wire everything together.** Build + test non-stop until the MVP is viable.

## MVP acceptance criteria ("viable")
1. Staff sets/【resets a 4–6 digit **PIN** at the console; staff logs into POS by PIN (scoped to their node/outlet).
2. POS order flow: tap items → cart → **checkout in ≤ a few taps** → pay **cash / card / PayNow** (mock) → success.
3. A diner can be attached (phone/scan) and **earn loyalty**; **vouchers + reward catalog redeem** at the till (reuse the voucher core).
4. **Receipt** renders/prints with company header + outlet/stall info (console-configured) + line items + totals + payment + any discount.
5. Console shows the resulting **transactions / sales report / redemptions** (reuse Reports/Orders; add a POS transactions view if needed).
6. Tenant-scoped + suspend-aware + PDPA-consistent; **tests green**; **proof in `artifacts/pos-proof/`** (screens + flow logs + bug log).

## Build areas (confirm "exists vs new" via the backend map)
- **Order/checkout core**: `create_manual_order` + `cashier_checkout` already exist → POS funnels through them.
- **Payments**: cash/card/nets/paywave/paynow already modelled (mock) → reuse; provider integration later.
- **Vouchers/rewards at POS**: reuse `POST /vouchers/{code}/redeem` + reward catalog redeem.
- **NEW — PIN auth**: a staff PIN (set/reset at console), a POS PIN-login endpoint → staff token scoped to outlet/node.
- **NEW — receipt config**: company header / outlet / stall fields (console settings) + a receipt payload/printable.
- **NEW — POS UI**: a fast, tablet-first ordering screen (`/pos`) — items → cart → pay → receipt; attach diner; redeem.
- **Console**: transactions/report/redemptions (mostly exist) + PIN management UI + receipt-header config UI.

## Method
Build + test non-stop, smallest vertical slices first, suite-green each, browser/Playwright-verified.
Spawn agents for mapping + parallel testing. Every slice → proof to `artifacts/pos-proof/` (screenshots,
flow transcripts, a `BUGLOG.md` of found→fixed). Self-improve until acceptance criteria pass.

## UI design (/my-uiux) — tablet-first, landscape
Flow: **PIN lock → Order (2-pane) → Pay sheet → Receipt**. Tap count (1 item, cash) = **4 taps**
(item → Charge → Cash → New order). Left pane = category chips + item grid (tap=+1); right rail =
running ticket + totals + discount, with **`+ Diner`** (phone→loyalty) and **`Voucher/Reward`**
(scan/enter) above a big **Charge $X** button (optional, no friction to the cash path). Pay sheet =
big method tiles (cash/card/paynow/nets/paywave, mock). Receipt = company header (console) + outlet/
stall + items/totals/payment/ref + Print. POS at `/pos`, device bound to an outlet once, then PIN-only.

## Backend map (confirmed) — build ON these
- `POST /orders/manual` (create_manual_order; order.manage) + `POST /orders/{id}/cashier-checkout`
  (payment.process; method cash|card|nets|paywave|paynow, mock) — the POS order+pay core EXISTS.
- `POST /vouchers/{code}/redeem` (staff) EXISTS. Reward-catalog redeem is **customer-only** (`/me/rewards/redeem`) → NEW staff-side needed.
- `User` has email+password, **NO pin** → NEW. CASHIER role = order.view/order.manage/payment.process.
- **No receipt config/print, no /pos UI, no staff reward redeem** → NEW.
- api-client lacks createManualOrder/cashierCheckout → add.

## Slice plan (vertical, suite-green + proof each)
1. **PIN auth** — User.pin_hash (per-merchant unique) + console set/reset + `POST /auth/staff/pin-login`.
2. **Receipt config + payload** — Merchant.settings receipt header (company/UEN/addr/phone/footer) + `GET /orders/{id}/receipt`.
3. **Staff reward redemption** — `POST /rewards/redeem-for` (staff redeems a catalog item for a diner onto an order).
4. **api-client** — createManualOrder, cashierCheckout, pinLogin, setStaffPin, getReceipt, staffRedeemReward.
5. **POS UI** `/pos` — PIN lock → order 2-pane → pay → receipt; diner attach; voucher/reward redeem.
6. **Console** — PIN mgmt (Team) + receipt-header config (Settings) + transactions/redemptions view (reuse Reports/Orders).
7. **Wire + e2e + proof** in artifacts/pos-proof/.

## Status: BUILDING — slice 1 (PIN auth)
