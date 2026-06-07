# FB Group — F&B CRM Platform PoC · Consolidated Delivery Report
_Singapore F&B CRM / QR ordering / loyalty / retention infrastructure._

## 1. Project summary
A merchant-first F&B retention platform. A diner scans a table QR, logs in, orders,
checks out (simulated payment), and earns loyalty points — and that activity
materialises in the merchant CRM (profile, spend, frequency, churn risk, segments).
A three-tier model — **Platform → Merchant (member-tree tenant) → Customer** — spans an ecosystem dashboard,
per-merchant CRM/analytics/pipeline/campaigns, and the customer ordering + rewards app.
Modular-monolith FastAPI backend (one API for all clients), Next.js frontend,
PostgreSQL, fully Dockerised and AWS-ready by design.

## 2. What was built
- **Backend** (`apps/api`): FastAPI + SQLAlchemy 2.0, **43 tables**, **137 API endpoints**, 24 Alembic migrations.
- **Member tree / Platform Console** (`/platform`): a single Chain/Storefront org spine you onboard + manage via UI — drill-down directory + `NodeDetailDrawer`; storefronts auto-provision their Outlet/Menu/QR; **Enter** any node to operate it scoped to its subtree. As-built spec: `docs/architecture-org-tree.md §12`.
- **Frontend** (`apps/web`): Next.js 14 App Router, **27 routes** (+ a `/showcase` UI-kit gallery), typed API client in `packages/api-client`. Customer app redesigned mobile-first on a shared **design system** (`packages/ui` tokens + component kit, Lucide icons). Includes the **staff POS** (`/pos`, PIN login, tap→pay, receipt, void).
- **Infra** (`infra/`): docker-compose (Postgres + API + web), Dockerfiles, healthchecks, backup script.
- **Docs** (`docs/`): architecture, api, security, testing, deployment, bc-dr, database, PRD, this report.
- **Proof** (`artifacts/`): pytest output + OpenAPI + sample JSON (CRM, segments, RFM, pipeline, campaigns…).

All 12 spec modules **plus** extensions: Platform Console; Salesforce-style Pipeline
(sales **and** win-back modes) / Activities / Activity timeline / Bulk actions / Record-owner;
RFM segmentation + win-back launcher (RFM→pipeline→campaign); spin-the-wheel reward game;
self-service admin (Menu, Users, **Tables & QR**, per-merchant feature toggles) on the **member-tree Platform Console** (Chain/Storefront onboarding & management);
**AI Insights advisor** (Claude-powered, with a deterministic heuristic fallback);
**888 Jackpot game** (server-authoritative match-3 on the menu, 5 coins/spin, a real **persistent progressive grand-jackpot pot** that grows over time and resets when won, mints food vouchers). Each game has its **own full-screen page** with a **win celebration** (fireworks + confetti). Loyalty currency is branded **"coins"** (not redeemable for cash — free items only).

## 3. How to run locally
**Docker (full stack on Postgres):**
```bash
docker-compose -f infra/docker-compose.yml up --build   # api :8000  web :3001 (host 3000 was taken)
```
The API container auto-applies migrations. **Seeding is OFF by default** (`SEED_ON_START=0`) — the DB
boots clean and merchants are onboarded via the Platform Console UI, or provisioned with the idempotent
ensure-script `python -m app.seed_demo_merchants` (see §4).
**Backend only (SQLite, fastest for tests):**
```bash
cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed && .venv/bin/python -m pytest      # 287 backend tests
.venv/bin/uvicorn app.main:app --reload                          # :8000/docs
```
**Frontend dev:** `cd apps/web && npm install && npm run dev`

## 4. Demo credentials (all merchant/operator logins `Password123!`)
The Docker stack boots **clean** (`SEED_ON_START=0`). Provision the demo merchants with the idempotent
ensure-script `python -m app.seed_demo_merchants` (rebuilds both groups + storefronts + the 3 logins with
fixed node ids → stable QR tokens; run after a data wipe). The old `owner@makan.sg` / `kampongeats.sg`
logins were **cleared** — they exist only in the legacy `app/seed.py`, which is **not** run on startup.

| Persona | URL | Login |
|---|---|---|
| Operator | http://localhost:3001/platform/login | superadmin@platform.sg |
| Merchant — **Breadtalk Group** (+ Bakery, Toast Box, Toast Box @ Taka/Orchard) | http://localhost:3001/merchant/login | owner@breadtalk.sg |
| Merchant — **Pepper Lunch Group** (+ all Pepper Lunch outlets) | (merchant login) | owner@pepperlunch.sg |
| Manager — **Toast Box @ Orchard** (single-storefront scope) | (merchant login) | manager@toastbox.sg |
| Customer | scan a live Storefront's table QR (see its *Tables & QR* page) | OTP phone `+6580000000` (DEBUG returns the code) |

Merchant logins are role = node-scoped **Manager** (owner-equivalent). Customer QR tokens are the live
storefronts' per-table QR codes (found in each Storefront's *Tables & QR* page), not static seed tokens.

## 5. Feature checklist
| # | Module | Status |
|---|---|---|
| 1 | Multi-tenant system — **Chain/Storefront member tree** (`org_nodes` spine; typed Merchant/Brand/Outlet/Table/QR = FK anchors) | ✅ |
| 2 | Customer identity & auth (OTP, email/pw, SSO-mock, JWT+refresh, rate limit) | ✅ |
| 3 | QR dining flow | ✅ |
| 4 | Menu & ordering (lifecycle, cashier/manual) | ✅ |
| 5 | Checkout & simulated payment (cash/card/NETS/PayWave/PayNow) | ✅ |
| 6 | Loyalty & rewards (earn rules, tiers, redemptions, coalition, **wheel game**) | ✅ |
| 7 | CRM (profiles, histories, churn, 8 segments, tags, notes) | ✅ |
| 8 | Promotions & campaigns (WhatsApp mock + retry, audience by segment, ROI) | ✅ |
| 9 | Sales reports, forecasts, graph APIs (+ **RFM**) | ✅ |
| 10 | Admin, roles & permissions (+ **user invite/revoke**, audit logs) | ✅ |
| 11 | Security standards (+ threat model) | ✅ |
| 12 | Reliability / BC-DR | ✅ |
| + | **Platform Console** (ecosystem KPIs, **member-tree directory** onboarding + drill-down; **Enter** any node → scoped console) | ✅ |
| + | **Salesforce CRM**: Pipeline/Opportunities (sales+win-back modes), Activity logging, Activity timeline, Record owner, Bulk actions | ✅ |
| + | **RFM** segmentation + **win-back launcher** (RFM→pipeline→campaign) | ✅ |
| + | **Self-service admin**: Menu CRUD (outlet/subtree-scoped), User invite/revoke, **Tables & QR** (per-table QR + print), member-tree node management, per-merchant feature toggles | ✅ |
| + | **AI Insights advisor**: executive summary + ranked next-best actions (Claude when keyed, deterministic heuristic otherwise) | ✅ |
| + | **888 Jackpot game**: server-authoritative match-3; 5 coins/spin; **persistent progressive grand-jackpot pot** (grows over time, resets on win); mints food vouchers | ✅ |
| + | **Customer app redesign**: mobile-first design system (`packages/ui` tokens + Lucide kit), 4-tab nav (Menu·Rewards·Orders·Me), order history, profile editor (mobile/birthday/gender), **dedicated full-screen game pages + win celebration (fireworks/confetti)** | ✅ |
| + | **Staff POS** (`/pos`): PIN login → tap→pay (cash/card/PayNow mock) → printable receipt; diner attach + voucher redeem at the counter; **Supervisor void** (reverse a paid sale → reports/payment/loyalty/voucher) | ✅ |
| + | **Web/POS login segregation**: `User.kind` — web logins (Manager/Staff/Finance, email+pw) vs **POS operators** (Supervisor/Cashier, PIN-only); PINs **encrypted at rest** (Fernet), owner-revealable, unique per storefront; auto-provisioned starter team (1 Supervisor + 2 Cashiers) | ✅ |
| + | **Vouchers**: shared core + 2 issuers (loyalty-earned / campaign-granted) + one cashier redeem flow (QR/code → discount), node-scoped, per-period cap, welcome-pack on signup | ✅ |
| + | **PDPA consent at capture** + **suspend enforcement** (login/order blocked for a suspended tenant) | ✅ |

## 6. Test results
- **Backend: 287 passed** (pytest, 48 files) — `artifacts/pytest_results.txt`. Covers auth, QR, ordering, checkout+loyalty (incl. order marked completed on payment), rewards/wheel, CRM + isolation, permissions, reports/forecast, the golden capture-loop e2e, operator, pipeline (modes)/activities/bulk/win-back, campaigns, menu/user/org admin, RFM, AI insights (heuristic path + permission/tenant gating), Kampong Eats merchant-4 seed (idempotency + menu shape), the 888 jackpot (grid/payline invariants, spin-cost deducted / insufficient-coins blocked, voucher mint), the customer **My Account** endpoints (order history + customer isolation, vouchers, profile get/update with phone required+unique), **per-merchant spin costs**, the **foodcourt** stall directory (`test_foodcourt.py`), the **loyalty posting ledger** (`test_loyalty_ledger.py`: domain stamp, balance==SUM(ledger) reconciliation, idempotent accrual, per-domain idempotency-key scoping), **POS order primitives** (`test_order_external_ref.py`), **module flags + boundary indirection** (`test_module_flags_boundaries.py`), the **org spine** (`test_org_tree.py`: parent/depth/path, sellable_under, network scope, two-world isolation), **RBAC node-cascade** (`test_rbac_node_cascade.py`: brand-scope cascade + cross-tenant isolation), **module gating** (`test_module_gating.py`: rewards_enabled off → 0 coins, qr_ordering_enabled off → 409, per-merchant), **loyalty-program admin** (`test_loyalty_admin.py`: get/update earn-welcome-birthday rules, earn=0 disables, staff/cross-tenant 403, module flags via settings, birthday bonus only in birthday month), **multiplier promotions** (`test_promotions.py`: engine applies in-window / skips expired+deactivated, **best-wins not stacked**, RBAC, cross-tenant 403/404), the **merchant orders feed** (`test_merchant_orders.py`: items+labels, status filter, outlet-scoped isolation, cross-merchant 403), and **logging behaviour** (`test_logging.py`).
  Plus this stretch: **PDPA consent** (`test_pdpa_consent.py`), **suspend enforcement** (`test_suspend_enforcement.py`), **vouchers** (core + cashier redeem + node scope + welcome pack), the **staff POS** (`test_pos_pin.py` — web/POS segregation, readable+encrypted per-storefront PINs, Supervisor/Cashier; `test_pos_receipt.py`; `test_pos_void.py` — supervisor void reverses sale/payment/loyalty/voucher), and the node→provisioned-outlet scope regression.
- **Frontend: 58 passed** (Vitest) — `artifacts/frontend_test_results.txt`.
- **Live HTTP** golden loop verified (`artifacts/live_demo.txt`); all 28 web routes return 200; Alembic up verified (roll-forward; CI checks upgrade-from-empty + drift, no downgrade-to-base).

## 7. Security checklist
Input validation (Pydantic) · ORM bound params (no SQLi) · bcrypt hashing · JWT
expiry + refresh + self-healing 401 · actor-separated auth · RBAC least-privilege ·
**tenant isolation (test-proven)** · rate limiting (OTP/login) · CORS allow-list ·
secure headers (HSTS/CSP/XFO/nosniff) · audit logs · env secrets / no hardcoded creds ·
server-side pricing · safe error responses. Full threat model + PoC limits: `docs/security.md`.

## 8. API documentation
Swagger `/docs`, ReDoc `/redoc`, machine spec `artifacts/openapi.json` (137 endpoints),
human reference `docs/api.md`.

## 9. Database schema (43 tables)
Tenancy, identity/RBAC, catalog, orders, payments, loyalty (+coalition), CRM
(tags/notes/segments), engagement (reward catalog, wheel, **jackpot**, tasks, opportunities,
activities), campaigns, audit. Diagram + grouping: `docs/database.md`;
list: `artifacts/schema_tables.txt`. UUID PKs, Numeric money, `merchant_id` isolation key.

## 10. Known limitations (PoC)
Payments, OTP, WhatsApp, Google/Apple SSO are **mocks**. In-process rate-limiter/OTP
(Redis in prod). JWT in localStorage for demo (httpOnly cookies in prod). Forecast is a
naive moving average. The **AI Insights advisor** calls Claude only when `AI_ENABLED=1`
+ `ANTHROPIC_API_KEY` are set; by default (and on any API failure) it runs a deterministic
heuristic — no key, network, or cost — which is what the PoC demos and tests use. Alembic
migrations target Postgres (SQLite dev/test uses `create_all`). No reward-expiry job or
campaign scheduler yet. **KIV:** win-back pipeline
auto-resolution (recovered/churned are set manually today). No referral program yet
(top growth lever — see roadmap).

## 11. Production-readiness roadmap
Swap mocks for real providers (Stripe/NETS/PayNow, SMS OTP, Twilio/Meta WhatsApp,
Google/Apple SSO) · Redis for limits/OTP/cache · **referral program** (top growth lever) ·
campaign scheduling + budget guardrails · win-back auto-resolution + reward-expiry jobs ·
cohort retention · AWS deploy (ECS Fargate + RDS Multi-AZ + ElastiCache + Secrets Manager
+ CloudFront/WAF + CloudWatch/OTel + blue/green) per `docs/deployment.md`;
RPO ≤5m / RTO ≤30m per `docs/bc-dr.md`.

## 12. Lead Verifier confirmation
All claims are backed by re-run tests + live HTTP verification against the Dockerised
Postgres stack. **The app runs; 287 backend + 58 frontend tests pass; the QR→order→
checkout→rewards→CRM capture loop works live; role/permission boundaries and
cross-merchant isolation are enforced and test-proven (22 dedicated isolation tests +
live adversarial proof — see §7); operator, pipeline (sales+win-back),
campaigns, menu/user/org admin, RFM, the win-back launcher, and the AI Insights advisor
all verified live.**
All 12 modules are met (plus extensions), with mocks for external providers as designed
for a PoC (explicitly listed in §10). Verified 2026-06-07 (counts + credentials current as of R39 —
POS MVP, web/POS login segregation, encrypted PINs, Supervisor/void, vouchers, PDPA/suspend).
