# Product Requirements (PoC)

## Vision
Merchant-first F&B retention infrastructure for Singapore: QR ordering + loyalty +
CRM + analytics that turns walk-in diners into known, retained customers.

## Target merchants
Fast-food chains, cafés, food courts (multi-brand, multi-outlet).

## Personas / admin structure
Platform Operator (Super Admin / Admin / Onboarding / Support) · Merchant Owner (tenant) ·
**two segregated login surfaces** (as-built R39): **web** node-assignable roles — Manager · Staff · Finance
(email+password, dashboard) — and **POS operators** — Supervisor · Cashier (PIN-only, `/pos`; Supervisor
adds void). Roles attach at any member-tree node; authority cascades down its subtree · Customer.
("Cashier" was dropped from the web palette → POS-only.)

## Phase-1 product (hybrid model)
QR ordering **and** cashier/manual checkout; loyalty works across both. Loyalty is
hybrid multi-tenant: merchant-isolated by default, with optional coalition rewards
across participating merchants. Points, tiers, campaigns, redemptions.

## The headline flow (capture loop)
Scan QR → register/login (OTP/email/SSO) → browse menu → order → checkout
(simulated payment) → earn points → **customer captured + profiled in merchant CRM**.

## Module status in this PoC
> These 12 are the **requirements baseline**. The authoritative **as-built status + extensions** (incl.
> the newer Staff POS, vouchers, PDPA consent, suspend enforcement) is **`delivery-report.md §5`** — the
> single source of truth, to avoid two drifting checklists.

| # | Module | Status |
|---|---|---|
| 1 | Multi-tenant merchant system | ✅ built + tested |
| 2 | Customer identity & auth (OTP/email; SSO mock) | ✅ built + tested |
| 3 | QR dining flow | ✅ built + tested |
| 4 | Menu & ordering (+ lifecycle, manual/cashier) | ✅ built + tested |
| 5 | Checkout & simulated payment | ✅ built + tested |
| 6 | Loyalty & rewards engine (+ coalition, multipliers) | ✅ built + tested |
| 7 | CRM dashboard (profiles, segments, churn, tags/notes) | ✅ built + tested |
| 8 | Promotions & retention campaigns (WhatsApp mock) | ✅ built + tested (audience by segment, mock send + retry, ROI metrics) |
| 9 | Sales reports, forecasts & graph APIs | ✅ built + tested |
| 10 | Admin, roles & permissions (+ audit) | ✅ built + tested |
| 11 | Security standards | ✅ implemented (see security.md) |
| 12 | Reliability / BC-DR | ✅ implemented-where-simple + documented |

### Extensions built on top (all ✅ built + tested)
- **Platform Console** — platform super-admin ecosystem dashboard, **member-tree** directory + onboarding, coalitions, drill-down; **Enter** any node for a console scoped to its subtree.
- **Salesforce-style CRM** — Pipeline/Opportunities (sales **and** win-back modes), Activity logging, Activity timeline, Record owner, Bulk actions.
- **Customer rewards** — redeemable catalog + **spin-the-wheel** game.
- **RFM segmentation** (Champions/Loyal/At-Risk/Hibernating…).
- **Win-back launcher** — RFM → win-back opportunities → WhatsApp campaign (retention loop).
- **Self-service admin** — Menu management (CRUD, outlet/subtree-scoped), User management (invite/assign/revoke), **member-tree node management + Tables & QR** (per-table QR + print), per-merchant feature toggles.
- **Staff POS** (`/pos`) — PIN login (segregated `kind="pos"`, encrypted PINs), tap→pay, receipt, diner attach + voucher redeem, **Supervisor void**.
- **Vouchers** — shared core + 2 issuers (loyalty/campaign) + one cashier redeem flow; node-scoped; welcome-pack on signup.
- **PDPA consent at capture** + **suspend enforcement** (login/order blocked for a suspended tenant).

## Out of scope (this round) / next steps
- Real Google/Apple SSO token verification; real OTP/WhatsApp/payment providers (Stripe/NETS/PayNow), refunds.
- **Referral program** (invite-a-friend, both-sided reward) — top growth lever (Luckin study).
- Cohort retention; campaign scheduling + budget/margin guardrails.
- **KIV:** win-back pipeline auto-resolution (auto-recover on next transaction; auto-churn sweep for stale win-backs).
- Reward-expiry job; per-merchant tier-benefit + RFM-threshold configurability.

## Non-functional requirements
Secure by default · tenant-isolated · tested · documented · Dockerized ·
AWS-ready by design · easy to run locally.
