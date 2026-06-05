# CLAUDE.md — working notes for this repo

FB Group: a Singapore F&B CRM / QR-ordering / loyalty PoC. Project overview and the
capture-loop diagram live in `README.md`. This file is operating guidance for Claude.

## Stack
- **Backend** `apps/api` — FastAPI + SQLAlchemy 2.0 (typed `Mapped`/`mapped_column`) + Alembic.
  Own Python venv at `apps/api/.venv` (NOT in the JS workspace). PyJWT HS256, bcrypt direct.
- **Frontend** `apps/web` — Next.js 14 App Router, `(customer)` + `(merchant)` route groups,
  SVG charts, **no Tailwind**. Vitest for tests.
- **Shared** `packages/` — `api-client` (typed client, alias `@fbgroup/api-client`), `ui`, `types`, `config`.
- **DB** — Postgres 16 in Docker for prod-like; **SQLite for pytest** (in-memory, StaticPool,
  `Base.metadata.create_all` — tests do NOT run through Alembic). Same ORM code both ways.
- **Infra** `infra/docker-compose.yml`. **Git repo** (origin `github.com/MetaliveSG/FB-Group`); branch +
  PR flow per `CONTRIBUTING.md` (no direct commits to `main`, conventional commits, add a migration for
  schema changes). "Save progress" = commit on a feature branch (+ memory for context not in code).

## Run & test
```bash
# Backend (fastest, SQLite):
cd apps/api && .venv/bin/python -m app.seed && .venv/bin/uvicorn app.main:app
cd apps/api && .venv/bin/python -m pytest          # backend tests
# Re-seed the SG-local merchant against live Postgres (idempotent, safe, no data loss):
cd apps/api && .venv/bin/python -m app.seed_kampong
# Ensure the demo merchants (Breadtalk Group + Pepper Lunch Group) + their 3 Manager logins —
# idempotent, additive, fixed node ids → reproducible QR tokens (against live Postgres):
cd apps/api && .venv/bin/python -m app.seed_demo_merchants
#   (or in Docker: docker-compose -f infra/docker-compose.yml exec api python -m app.seed_demo_merchants)
# Full stack (Postgres + API + web):
docker-compose -f infra/docker-compose.yml up --build
# Frontend:
cd apps/web && npm install && npm run dev      # dev
cd apps/web && npm run test                    # Vitest
```
Baseline: **230 backend + 45 frontend tests pass** · ~120 endpoints · 42 tables · 17 migrations.

## Member tree (org spine) — Chain / Storefront
The org tree has **two node kinds** (engine keys off the `sells` flag; `role` is a display label):
**Chain** (structural — nests Chain/Storefront children; optional *stop-chain* → storefronts-only)
and **Storefront** (`sells=true` — the leaf that has the menu / takes orders). Boundary flags
(`is_settlement_boundary` + `is_loyalty_domain`) mark the **tenant** ("merchant"). Authority =
tree position × cascade; node-assignable role palette **Manager/Cashier/Staff/Finance**. Managed
from the **Platform Console** (`/platform`) directory drill-down: rows are clean (`badge · name ·
⋯`); the **⋯ opens a NodeDetailDrawer** (rename · status · subscription fee · stop-chain · add
child · node logins · enter). Endpoints: `GET /org/tree`, `POST/PATCH /org/nodes`,
`GET/POST/DELETE /org/nodes/{id}/accounts`. Proof: `artifacts/breadtalk-member-tree/`.
**As-built grounding — see `docs/architecture-org-tree.md §12`** (the authoritative as-built spec):
- **Provisioning** (`app/services/storefronts.py`): creating a Storefront (`POST /org/nodes` or a
  `member_kind=storefront` tenant) auto-mints its typed `Outlet` + **`Menu` with `id == node.id`** +
  `DiningTable` + stable `QRCode`. **`menu.id == node.id` is the invariant the resolvers key off.**
  Idempotent; `provision_missing()` backfills. Never run `sync_org_tree` on UI-built trees (re-parents).
- **QR resolution = 3 functions, 3 radii:** directory **"QR Menu"** link (`org.py::_qr_paths_for`,
  node-keyed — Storefront→`/t/{own outlet token}`, Chain→`/t/node/{id}` iff it has direct storefronts) ·
  **group browse** `/t/node/{id}` = `catalog.direct_storefronts` (**DIRECT** children + directly-leased,
  NOT nested-under-sub-chain) · **venue scan** `/t/{token}` = `catalog.list_outlet_stalls` (house ∪
  leased). `node_scope_stalls` (whole subtree) is for menu-reachability validation only.
- **Tables & QR** (`/merchant/tables`): per-table QR via `qrcode.react` (encodes `{origin}/t/{token}`) +
  Print/Print-all; add-table = fixed `T` prefix + number stepper (auto-next, padded `T01`…).
- **Enter scopes by the node** (`OperatorMerchant {id=tenant, nodeId, outletId?}`): Storefront → locked
  to 1 outlet; **any sub-chain → its subtree** (`menu-admin/outlets?node_id=`); tenant → all. Menu +
  Tables & QR sub-scope; **CRM/Orders/Settings stay tenant-wide** (loyalty ring = the tenant). Full nav
  shows in every mode; **Brands & Outlets are no longer a managed UI** (typed FK anchors only).

## Vouchers & redemption (decided 2026-06-05 — see `docs/architecture-vouchers.md`)
**Shared Voucher core, two issuers, one redemption.** A voucher carries `value` + rules (single-use ·
valid window · **per-day/week/month cap** · min-spend) and is redeemed by ONE cashier flow (scan QR /
enter code → validate → mark used → apply to the order, on the checkout/`record_sale` path).
**Loyalty** = the *earned* issuer (points catalog · birthday · wheel/jackpot; configured in Settings).
**Campaign** = the *granted* issuer (welcome pack · referral · promo · win-back). Litmus: *earned,
always-on, everyone* → loyalty; *granted to a trigger/segment* → campaign. So a **welcome "10×$1 on
signup, 1/period"** = a **campaign** (trigger=register) issuing from the core; **"$1 off for N coins"** =
**loyalty** — both redeemed the SAME way. Mirrors BreadTalk (Welcome eVoucher vs points Bun Voucher).
**As-built gap:** issuance works (`RewardRedemption` + `voucher_code` from catalog/wheel/jackpot) but
the **cashier redeem half is NOT built** (no validate/mark-used/apply-to-order; no rules; status
`redeemed`/`active` inconsistent). Build order: core+redemption → issuance hooks → UI.

## Roadmap & next phases (priority) — see memory `roadmap-mvp-foundation`
**DIRECTION = MVP, not PoC (2026-06-04).** Bar = "a first real merchant runs their business on this"
(not demo/proof). Local-first still holds (no premature cloud). The MVP merchant is **fully on our
stack**: every sale goes through **our** channels (table QR · our cashier POS · mobile/web app) → every
sale is ours, already uniquely id'd → **no "outside" sale, no external-reference/receipt-dedup in the
MVP.** "POS link-up" = OUR cashier POS (built: `create_manual_order`+`cashier_checkout`), NOT external-POS.
**MVP definition-of-done (status in memory `roadmap-mvp-foundation`):** ✅ capture loop · onboarding ·
reports+SEA-tz · CRM · rewards · RBAC. Remaining — **PDPA consent at capture** (one new add) · suspend
enforced at login/order · `record_sale()` convergence · **unified tree-scoped console** (plan-first:
`docs/architecture-unified-console.md` — operator at tree root, scope-down, fixes the "missing merchant
id" bug) · **cashier POS on the merchant's device** (MVP bridge = PWA-on-Android + BT printer; real
terminal = Android POS phase) · day-end closing · first-merchant go-live + demo polish.
*Optional foundation tidy:* extract a shared `record_sale()` core so the 3 channels converge and external
doors are a trivial add later — not a blocker. *Do NOT build:* external-POS ingestion/receipt-dedup
(keep-your-POS = P1), aggregator pull-in (P5), venue/lease/settlement/franchising/Storefront-re-key.
**Foundation Contract (7 guarantees, keep future phases additive — no restructure):** ① `org_nodes`
= canonical spine, typed tables = profiles+FK anchors (MVP keeps `Order.outlet_id`; future adds
`storefront_id` alongside) · ② stable IDs forever (`node.id==profile.id`) · ③ flag-based RBAC via the
spine · ④ money=Decimal, settlement/loyalty resolved on the node · ⑤ one QR/token→context resolver
(`qr.py`; outlet = a *location/venue*, menu = the *seller* — never bake "outlet == sellable unit") ·
⑥ one `record_sale()` core all channels funnel through (MVP = our QR/POS/app converge to it; external
doors — keep-your-POS/receipt/aggregator — are additive callers later, no new plumbing) · ⑦ everything behind capability flags.
**Moats** (see memory `moat-register`): **M1** data network · **M2** split settlement · **M3** member-tree
model (BUILT) · **M4** SEA operating-model/compliance · **M5** lock-in. Each phase is tagged with the
moat it builds — never ship a phase without knowing which defensibility it serves.
**MVP** → locks the Foundation Contract (*protects* M3) + seeds **M1** (capture identity) & **M5** (CRM/coin lock-in).
**Phases (priority):**
- P1 ★★★ **commission-escape** → **builds M1** [+M5] — node-addressable brand/group apps + takeaway/
  delivery + referral loop + finish PDPA. *The wedge: own your customer, escape ~30% aggregator fee.*
- P2 ★★★ **multi-party settlement + venue/lease** → **builds M2** [+M4] — foodcourt GTO vs coffeeshop
  fixed-rent; split settlement. *The crown-jewel moat.*
- P3 ★★ **franchising / value-rollup** → **builds M2·M5** [+M4] — royalty rollup + central menu; the Storefront re-key.
- P4 ★★ **AI ops** → **deepens M1** [+M4] — demand → labour + waste markdown (moat only via the cross-merchant data).
- P5 ★ **ops depth** → **builds M5** — KDS/inventory/aggregator pull-in (become the primary screen; selective).
- **Android POS** ★★★ (HARDWARE, pulled forward by the real onboarding) → **builds M5** [+M1] — real
  cashier terminal (Sunmi/iMin/PAX: thermal printer + drawer + offline + card). MVP bridge = PWA-on-
  Android-tablet + BT ESC/POS printer NOW; native (Expo/RN) or Capacitor wrapper as the terminal. Depends
  on `record_sale()` core + day-end closing. See memory `android-pos-phase`.
Cross-cutting (NOT MVP): real providers (NETS/PayNow/Stripe, WhatsApp BSP) → **M4**+protect M1 trust;
scale stack (Redis/queues/websockets — arrive P2/4/5); staging+IaC+AWS. Compliance (PDPA/Nutri-Grade/
GST/CDC/MAS) → **M4** (the barrier to entry). GTM keep-your-POS → `gtm-pos-agnostic-capture` (feeds M1/M5).

## Environment gotchas (this machine)
- Docker CLI is **`docker-compose`** (hyphenated v1), NOT `docker compose` v2.
- Web is mapped to host **:3001** (host 3000 was taken); API on :8000; Postgres on :5432.
  API CORS allows both 3000 + 3001. API `DEBUG=true` in compose → OTP returns `debug_code`.
- DB creds (compose): user/pass/db all `fbgroup`. Connect tools to `localhost:5432`.

## Conventions & traps
- **Multi-tenant**: nearly every query is scoped by `merchant_id`. Lead with it in any composite index.
  Operator (super_admin) drills into merchants via `?merchant_id=`.
- **Money** = `Numeric(12,2)` as Python `Decimal`. **PKs** = `String(32)` hex UUID (`uuid4().hex`).
  **Timestamps** = naive UTC (`app/db/base.py::utcnow`); SG is UTC+8.
- **VARCHAR length**: SQLite tests do NOT enforce it; Postgres does. A value that fits in SQLite
  can 500 on Postgres (bit us once with a voucher code in `reward_redemptions.status`). Verify on PG.
- **Alembic migrations target Postgres natively** (plain `op.create_table`); they can't run on SQLite.
- **api-client types can claim fields the backend schema doesn't return** — TS compiles, runtime crashes,
  and only on the non-empty path. Keep `packages/api-client` types in sync with `app/schemas`.
- **Idempotent seed pattern**: `seed_kampong` / `_ensure_kampong_jackpot` do insert+update+remove keyed
  by stable name (with an empty-seed guard). "Edit the seed → re-run → live reflects it", no migration.
- **Provider mocks** (OTP / WhatsApp / AI insights): mock by default; real provider only when a flag +
  key are set (e.g. `AI_ENABLED=1` + `ANTHROPIC_API_KEY`). Tests/demo use the deterministic mock path.
- **Report timezone — ONE tz per report (default SG); Phase 1 done, DST-correct.** Timestamps are
  stored naive-UTC (canonical instant); reports localise at read via `app/analytics/timezones.py`
  (`to_local` = `zoneinfo`, DST-correct; `local_day_bounds_utc` = inclusive local days → HALF-OPEN UTC
  bounds; `valid_tz`). `tz` is threaded through bucketing (`sales`/`peak_hours`/`forecast`) + a per-request
  `?tz=`; **default `Asia/Singapore`** → SG output unchanged. `_txns` range is half-open `[start, end)`.
  **The report tz is a SINGLE value for the whole report AND its drill-down** — so parent total == Σ
  children and the date window is unambiguous.
  **Phase 2 — BUILT (tenant-level tz + display dropdown).** `routes/reports.py::_tenant_tz` resolves the
  ONE report tz: `explicit ?tz=` → `Merchant.settings["timezone"]` (the tenant's canonical reporting tz =
  the "books"; settable in merchant Settings, strict-validated → 422 via `timezones.require_tz`) →
  platform default. `_scope` returns it; `/reports/summary` echoes `timezone` so the UI labels it. The
  Reports page has a **timezone dropdown** that defaults to the tenant tz (NOT the viewer's) and is a
  **display override** — picking another shows a "differs from the business reporting timezone" banner
  (official totals/payout/GST use the tenant tz). **NEVER derive the report tz from `Outlet.timezone`** —
  a parent spans many outlets, so a per-outlet tz makes `from`/`to` ambiguous and breaks parent↔child
  reconciliation. `Outlet.timezone` stays reserved for a future opt-in single-outlet "in this store's
  local time" leaf view only. **Phase 3 (deferred):** business-day start (e.g. 4am close, Square/Toast).

## Where things are
- `apps/api/app/models/*.py` — schema (source of truth) · `app/services/` — business logic (ORM only, no raw SQL)
- `app/analytics/` — read-heavy paths (`reports.py`, `rfm.py`, `crm.py`) · `app/loyalty/engine.py` — hot accrual path
- `docs/` — `delivery-report.md` (canonical current state), architecture/api/database/security/testing/deployment/bc-dr/PRD
- `artifacts/` — generated proofs (openapi.json, pytest_results.txt, sample JSON, demo_credentials.md)
- `queries/` — ready-to-run diagnostic SQL (run via SQLTools or `psql -f`); see header in `01_customer_lookup.sql`
- `.vscode/` — SQLTools connection to the Docker Postgres + recommended extensions

## Demo credentials
- Operator: `http://localhost:3001/platform/login` → `superadmin@platform.sg` / `Password123!`
- Merchant dashboard: `http://localhost:3001/merchant/login` (live UI-onboarded merchants; the old
  seeded `owner@makan.sg` was cleared). All `Password123!`, role = node-scoped **Manager** (owner-equiv):
  - `owner@breadtalk.sg` → **Breadtalk Group** (+ downline: Bakery, Toast Box, Toast Box @ Taka/Orchard)
  - `owner@pepperlunch.sg` → **Pepper Lunch Group** (+ all Pepper Lunch outlets) *(genuine Merchant-Owner from onboarding; pw reset to the standard)*
  - `manager@toastbox.sg` → **Toast Box @ Orchard** only (single-storefront scope)
  - Durable via the ensure-script: `python -m app.seed_demo_merchants` (idempotent; rebuilds both
    groups + storefronts + these 3 logins with fixed node ids → stable QR tokens). Run after a data wipe.
- Customer QR: scan tokens are the live storefronts' QR (see each Storefront's *Tables & QR*); OTP phone `+6580000000` (DEBUG returns the code).

## Memory & skills
- Persistent memory: `~/.claude/projects/-Volumes-Data-Drive-Coding-multi-agent-FB-Group/memory/`
  — `MEMORY.md` index + `build-state.md` (canonical Round log + KIVs), `project-fbgroup-crm.md`, `arch-decisions.md`, `user-prefs.md`.
  Run `/my-catchup` at session start; `/my-wrapup` to close out (updates memory + regenerates artifacts).
- Project skills in `.claude/skills/`: `/my-architect`, `/my-tester`, `/my-security-audit`, `/my-dba`,
  `/my-ops`, `/my-diagnose`, `/my-bizdev` (advisors) + `/my-catchup`, `/my-wrapup` (lifecycle).

## How the user works (Founder Mode)
~2-person team + Claude Code. Prioritize speed, working+tested software, revenue/adoption — while keeping
strong security/testing/architecture standards. Be decisive; prefer prose planning over multiple-choice
prompts. Don't claim completion without passing tests + proof of the demo flow.
