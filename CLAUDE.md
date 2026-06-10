# CLAUDE.md — working notes for this repo

## Product: Customer Intelligence Platform (CIP)
**The system is "Customer Intelligence Platform" (CIP)** — helps F&B merchants **grow using customer
intelligence**: five modules **CRM · AI · Payment · Ordering · Rewards**, positioned as *intelligence-led
growth* (data from ordering/payment/rewards feeds the CRM+AI). Repo/codename "FB Group" (SG F&B PoC→MVP).
Maps to the 3-module engine (Table QR · **Intelligence** · POS) on one core — `docs/architecture-3-modules.md`.
Overview + capture-loop diagram in `README.md`; this file = operating guidance for Claude.
**Pitch · growth model · GTM** → `docs/positioning.md` (or `/my-bizdev`).

## Customer-scan domains (QR · LOCKED 2026-06-10)
**The customer-scan surface is served per-tenant on a CIP subdomain: `{slug}.mycip.io`** (e.g.
`breadtalk.mycip.io`, `fsg.mycip.io`). **Apex/root brand domain = `mycip.io`.** A printed QR therefore
encodes **`https://{slug}.mycip.io/t/{token}`** (a Storefront) or `…/t/node/{id}` (a group browse).
- **The QR host comes from PER-TENANT config, never the browser.** *Current gap:* `apps/web/.../merchant/
  tables/page.tsx` builds the URL from `window.location.origin` (→ `localhost:3001` in dev) — that's
  PoC-only and MUST be replaced by a tenant-resolved scan base before any real QR is printed (printed codes
  are permanent). Same for the `/platform` "QR Menu" button + on-screen preview. Backend `qr_path` stays a
  relative `/t/{token}` — only the web layer prepends the origin, so the fix lives there (+ a backend
  resolver that emits the canonical `{slug}.mycip.io` host per tenant).
- **`slug`** = a new per-tenant field (settlement-boundary node / `Merchant`), unique, → its subdomain. NOT
  built yet.
- **Routing:** wildcard `*.mycip.io` DNS → ONE CIP edge → the same Next app serves `/t/{token}` regardless
  of `Host`; the **token alone identifies the outlet** (host = branding + trust). Validate the token's
  tenant matches the host's tenant (so a competitor's QR can't resolve on your branded subdomain).
- **TLS:** one wildcard cert `*.mycip.io` covers every tenant subdomain.
- **DEFERRED (Tier 3, post-MVP):** BYO **custom domains** (e.g. `order.fairprice.sg`) — tenant CNAMEs to CIP
  + per-domain cert automation (ACM/Caddy) + a `tenant_domains` verification table. Subdomain is the locked
  default; custom-domain is later config on the same resolver, never a reprint. Keep retired hosts 301-ing.

## Kitchen display (KDS · LOCKED 2026-06-10)
**The kitchen screen (`/kds`) is a back-of-house DISPLAY, not a dashboard.** Auth model = **station binding,
NOT a web/email login and NOT a per-person password** (a kitchen tablet is a shared station; per-cook
attribution is not needed for MVP). The "role" (view this outlet's open tickets + advance ticket status) is
**baked into a private, revocable per-outlet station token** issued from the console — NOT the public QR
token (that's semi-public; a separate private token so nobody with a table's QR can open the kitchen). A
`RoleName.KITCHEN` PIN role on the **POS palette** (`kind="pos"`, never web) is the LATER upgrade only if
per-person attribution is wanted. **Gate = Table QR effective-ON** (`resolve_modules`) controls whether the
kitchen screen is reachable; the module flag gates ACCESS, never credential lifecycle (don't mint/destroy
credentials on a toggle flip — it cascades + churns PINs).
- **Fulfilment vs payment are SEPARATE statuses (decided 2026-06-10).** `checkout()` sets `order.status`
  COMPLETED on pay (COMPLETED = *paid*, drives reports/void — do NOT repurpose it). The kitchen owns a
  separate additive **`fulfilment_status`** (QUEUED→PREPARING→READY→COLLECTED) — the ticket/KDS state,
  orthogonal to payment. **"Pick up" button = mark READY** (customer collects from the stall — the
  order-ahead+pay+collect model). KDS queue = paid orders (`status=COMPLETED`) where
  `fulfilment_status≠COLLECTED`, oldest-first (FIFO).
- **Preview slice (built 2026-06-10):** `/kds` runs in the MERCHANT/operator session (owner previews it);
  the station-token issue/revoke is the hardening step (deferred). Launched standalone (new window) from the
  `/platform` tree-grid "Open Kitchen" (gated on Table-QR) + `/merchant/orders`.

## Stack
- **Backend** `apps/api` — FastAPI + SQLAlchemy 2.0 (typed `Mapped`/`mapped_column`) + Alembic.
  Own Python venv at `apps/api/.venv` (NOT in the JS workspace). PyJWT HS256, bcrypt direct.
- **Frontend** `apps/web` — Next.js 14 App Router, **flat route segments** (`t/` customer · `merchant/`
  dashboard · `platform/` operator · `pos/` staff POS — NOT parenthesised route groups),
  SVG charts, **no Tailwind**. Vitest for tests.
- **Shared** `packages/` — `api-client` (typed client, alias `@fbgroup/api-client`), `ui`, `types`, `config`.
- **DB** — Postgres 16 in Docker for prod-like; **SQLite for pytest** (in-memory, StaticPool,
  `Base.metadata.create_all` — tests do NOT run through Alembic). Same ORM code both ways.
- **Infra** `infra/docker-compose.yml`. **Git repo** (origin `github.com/MetaliveSG/FB-Group`); branch +
  **commit directly to `main`** (no PR flow — user's call 2026-06-07; branch protection removed); conventional
  commits, add a migration for schema changes. CI still runs on push (informational, non-blocking — watch
  it). "Save progress" = commit on `main` (+ memory for context not in code).

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
Baseline: **291 backend + 63 frontend tests pass** · 136 endpoints · 43 tables · 26 migrations.

## Member tree (org spine) — Chain / Storefront

**GLOSSARY — grounded terms (don't invent; these are the engine truth, `app/models/org.py`):**
- **OrgNode** — one node of the member-tree spine. **`role` is a DISPLAY LABEL only** (`CHAIN`|`STOREFRONT`); the engine keys off **flags**, never the label.
- **Canonical node kinds = TWO:** **CHAIN** (structural; nests) · **STOREFRONT** (`sells=true`; the orderable leaf with a menu).
- **The two boundary flags (the real truth):** **`is_settlement_boundary`** = collects money/GST/payout · **`is_loyalty_domain`** = the coin-ring boundary. Resolved per node to `settlement_account_id` / `loyalty_domain_id` (nearest declaring ancestor).
- **Tenant = Merchant** = a node with **`is_settlement_boundary=true`** (today both flags sit together on the group). "Tenant-level / merchant-level" = **one shared thing for that whole boundary + all its storefronts** (coin balance, CRM list, jackpot pot/prizes).
- **Storefront-level / per-node** = set per outlet via the **cascade** (the on/off module + game toggles; that store's menu/tables/till). Shared *data* is tenant-level; *participation* (does this store earn/order/ring/spin) is per-node.
- **Enterprise** = **NOT a built node type** — a *concept + legacy label only* (`RoleName.GROUP_*` bundles, demo-seed; `architecture-org-tree.md §ENTERPRISE` = NOT built). If ever built it's just **a top CHAIN node carrying `is_loyalty_domain`** above several merchant (settlement-boundary) nodes → one ring across them, while **settlement stays per-merchant**. Cross-*different*-enterprise rings = coalition/clearing (M2, deferred).
- **LEGACY role labels (demo-seed only, superseded):** `ENTERPRISE/MERCHANT/BRAND/OUTLET/STALL` + `GROUP_*/AREA_MANAGER/STALL_OPERATOR`. Current palettes: **web** = manager/viewer/finance · **POS** = supervisor/cashier (see roles bullet below).

**Two node kinds** (engine keys off `sells`; `role` is a display label): **Chain** (structural, nests;
optional stop-chain → storefronts-only) · **Storefront** (`sells=true`, has the menu). Boundary flags mark
the **tenant**. Authority = tree position × cascade. **Two SEGREGATED login surfaces:** web (email+pw,
dashboard) = **Manager/Viewer/Finance** · POS (PIN-only, `/pos`) = **Supervisor/Cashier**. Managed from the
**Platform Console** (`/platform`) drill-down → `NodeDetailDrawer` (rename · status · fee · stop-chain · add
child · module toggles · logins · enter). Endpoints: `GET /org/tree`, `POST/PATCH /org/nodes`,
`GET/POST/DELETE /org/nodes/{id}/accounts`, `GET/PUT /org/nodes/{id}/modules`.
**Full as-built spec → `docs/architecture-org-tree.md §12`**; POS/roles detail → memory `roles-reference` +
`pos-mvp`; vouchers → `docs/architecture-vouchers.md`. **Critical invariants / traps (do NOT violate):**
- **`menu.id == node.id`** — the invariant all resolvers key off. Storefronts auto-mint Outlet+Menu(id==node)
  +Table+QR (`services/storefronts.py`, idempotent; `provision_missing()` backfills).
- **Never run `sync_org_tree` on UI-built trees** (it re-parents → silently breaks FIXED-rent isolation).
- **node→outlet goes THROUGH `Menu.id==node.id`, never assume `outlet.id==node.id`** (only true for the
  legacy/collapsed seed; provisioned storefronts have a separate outlet uuid).
- **QR resolution = 3 radii:** directory "QR Menu" (`org.py::_qr_paths_for`, node-keyed) · group browse
  `/t/node/{id}` = `catalog.direct_storefronts` (DIRECT children only) · venue scan `/t/{token}` =
  `catalog.list_outlet_stalls` (house ∪ leased).
- **Node-browse UX (INTENDED, `t/node/[id]/page.tsx`):** **1 direct stall → auto-enter that stall's
  menu/ordering** (skips the list — straight to its items); **2+ stalls → show the group stall list**. So a
  sub-chain with a single child jumps straight into that child (NOT a bug). If it looks "empty", the stall's
  **menu has 0 items** (data), not a nav bug — menu items are live data, NOT in `seed_demo_merchants` (e.g.
  Pepper Lunch Sub @ YIS had 0 items while siblings had ~17).
- **POS = `User.kind="pos"`**, synthetic `@pos.local` + locked pw (can't web-login; web can't PIN-login);
  PINs **encrypted at rest** (Fernet, `core/pin_crypto.py`), unique per storefront. Supervisor = Cashier +
  `order.void` (`POST /orders/{id}/void` reverses sale/payment/loyalty/voucher; receipt → Supervisor-PIN modal).
- **Enter scopes by node:** Storefront → 1 outlet; sub-chain → its subtree; tenant → all. Menu + Tables&QR
  sub-scope; **CRM/Orders/Settings stay tenant-wide** (loyalty ring = the tenant).

## Vouchers (decided 2026-06-05 — full spec `docs/architecture-vouchers.md`)
**Shared Voucher core, two issuers, one redemption.** Carries `value` + rules (single-use · valid window ·
per-period cap · min-spend); redeemed by ONE cashier flow (scan/enter code → validate → apply, on the
checkout/`record_sale` path). **Litmus:** *earned, always-on, everyone* → **loyalty** issuer; *granted to a
trigger/segment* → **campaign** issuer — both redeemed the SAME way (welcome "10×$1/period" = campaign;
"$1-off for N coins" = loyalty). **Scope** = a node, reach = its subtree (`scope_node_id`; `merchant_id` =
funding tenant). Tiers 1–2 BUILT; tier 3 (cross-merchant = coalition + split-settlement M2) DEFERRED.

## Roadmap (DIRECTION = MVP, not PoC — full detail: memory `roadmap-mvp-foundation`)
Bar = "a first real merchant runs their business on this". MVP merchant is **fully on our stack** (every
sale via our QR/POS/app → already uniquely id'd → **no external-POS/receipt-dedup in MVP**).
**Foundation Contract (7 guarantees, keep phases additive):** ① `org_nodes` = canonical spine, typed
tables = FK-anchor profiles · ② stable IDs (`node.id==profile.id`) · ③ flag-based RBAC · ④ money=Decimal,
settlement/loyalty resolved on the node · ⑤ one QR→context resolver (`qr.py`) · ⑥ one `record_sale()` core
all channels funnel through · ⑦ everything behind capability flags.
**Phases:** P1 commission-escape (M1) → P2 multi-party settlement+venue/lease (M2) → P3 franchising/rollup
→ P4 AI ops → P5 ops depth; **Android POS** (M5, hardware, pulled forward — PWA+BT bridge now → native).
**Moats** (memory `moat-register`): M1 data network · M2 split settlement · M3 member-tree (BUILT) ·
M4 SEA compliance · M5 lock-in. **Do NOT build:** external-POS ingestion/receipt-dedup, aggregator pull-in,
venue/lease/settlement/franchising/Storefront-re-key (all post-MVP).

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
- **Report timezone — ONE tz per report (whole report AND its drill-down), default `Asia/Singapore`.**
  Timestamps stored naive-UTC, localised at read (`app/analytics/timezones.py`; half-open `[start,end)`
  bounds). Tenant tz = `Merchant.settings["timezone"]` (resolved `?tz=` → tenant → platform in
  `routes/reports.py::_tenant_tz`); the Reports dropdown is a display-only override. **NEVER derive the tz
  from `Outlet.timezone`** (a parent spans many outlets → ambiguous window, breaks parent↔child recon).
  Full design + Phase 1/2/3 → `docs/reporting-timezone.md`.

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
