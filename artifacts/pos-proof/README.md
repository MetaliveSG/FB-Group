# POS MVP — proof of viability

Flow transcripts + screenshots + acceptance-criteria results. See BUGLOG.md for found/fixed defects.

## E2E run 1 (2026-06-05) — full flow PASS
Setup (bind Pepper Lunch @ TPY via QR) → PIN unlock (2580) → order (2× Beef Pepper Rice + 1× Chicken
Pepper Rice) → Charge $34.70 → pay CASH → receipt (Pepper Lunch Pte Ltd header, TOTAL $41.61, CASH +
mock ref, footer). 5 menu items loaded; zero page errors. Screens: 01_order.png, 02_receipt.png.
Acceptance covered: 1 (PIN login) · 2 (tap→pay, ~4 taps) · 4 (receipt w/ console header) · payments mock.
Pending UI: console PIN-mgmt + receipt-config screens (slice 6); diner/voucher redeem at till (wired, e2e next).
