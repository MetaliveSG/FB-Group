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
