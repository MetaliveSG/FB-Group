# CLAUDE.md — working notes for this repo

## Product: Customer Intelligence Platform (CIP)
**The system is "Customer Intelligence Platform" (CIP)** — helps F&B merchants **grow using customer
intelligence**: five modules **CRM · AI · Payment · Ordering · Rewards**, positioned as *intelligence-led
growth* (data from ordering/payment/rewards feeds the CRM+AI). Repo/codename "FB Group" (SG F&B PoC→MVP).
Maps to the 3-module engine (Table QR · **Intelligence** · POS) on one core — `docs/architecture/architecture-3-modules.md`.
Overview + capture-loop diagram in `README.md`; this file = operating guidance for Claude.
**Pitch · growth model · GTM** → `docs/business/positioning.md` (or `/my-bizdev`).

## Decision register — `docs/decisions.md` (THE authority on what's decided)
**When the user firms a major decision** ("locked" / "agreed" / "go with X" / overruling a design),
**append a row to `docs/decisions.md` IN THE SAME TURN** — date · decision · why · status · supersedes —
and mark any overruled row `SUPERSEDED` (never delete). Don't wait for wrapup (`/my-wrapup` only sweeps
for missed rows; `/my-catchup` reads recent rows). The register outranks memory prose and doc narrative
when they disagree.

## Customer-scan domains (QR · LOCKED 2026-06-10 → `docs/architecture/architecture-scan-domains.md`)
Per-tenant scan host = **`{slug}.mycip.io`** (apex `mycip.io`); printed QR encodes
`https://{slug}.mycip.io/t/{token}` (or `…/t/node/{id}`). **The QR host comes from PER-TENANT config,
never `window.location.origin`** — the tables page + `/platform` QR button do it the PoC way today and
MUST be fixed before any real QR prints (printed codes are permanent). Backend `qr_path` stays relative;
validate the token's tenant matches the host's tenant. `slug` field + tenant resolver NOT built; BYO
custom domains = post-MVP (Tier 3).

## Kitchen display (KDS · LOCKED 2026-06-10 → `docs/architecture/architecture-fulfilment-modes.md` §KDS)
`/kds` is a back-of-house DISPLAY. Auth = **station binding** (private, revocable per-outlet station
token) — NOT a web login, NOT a per-person PIN; Table-QR effective-ON gates ACCESS, the flag never
drives credential lifecycle. **Fulfilment ≠ payment:** additive **`fulfilment_status`**
(QUEUED→PREPARING→READY→COLLECTED); `order.status` COMPLETED stays = *paid* (drives reports/void — do
NOT repurpose). KDS queue = paid ∧ not-collected, FIFO. Preview slice runs in the merchant session;
station-token issue/revoke deferred.

## Service options (fulfilment · LOCKED 2026-06-10 → `docs/architecture/architecture-fulfilment-modes.md`)
**TWO orthogonal axes, NOT a single "dine-in vs pickup" mode:** dining context (`eat_in|takeaway` →
plate/package, table?) × hand-off (`self_pickup|served`). **KEY RULE: the diner "ready for pick-up"
alert keys off `self_pickup`, NOT "dine-in".** The storefront configures its enabled SET (cascade like
module flags — a foodcourt sets it once high, stalls inherit); the diner picks per order if >1. SEA
default = Self-Service + Takeaway. BUILT 2026-06-10/11 (cascade config + drawer control +
`Order.hand_off` + per-order picker + KDS cue + ready notification, ≤6s poll). **Per-stall options in a
foodcourt = DEFERRED into M2** (foodcourt orders attribute to the venue outlet until M2 stall
attribution). Still open: `pickup_number` · conditional table · real push (SSE/Web Push) · per-item
availability by option · service-charge keyed off `served` (self-collect wrongly charged today).

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
# Fei Siong Group (FSG) ENTERPRISE demo — the pitch tree, Malaysia Boleh! foodcourt + 6 real stalls w/ menus
# (idempotent; FSG enterprise → Malaysia Boleh! tenant → stalls; owner@malaysiaboleh.sg / Password123!):
cd apps/api && .venv/bin/python -m app.seed_fei_siong   # → memory fsg-enterprise, menu-modifier-groups
# Full stack (Postgres + API + web):
docker-compose -f infra/docker-compose.yml up --build
# Frontend:
cd apps/web && npm install && npm run dev      # dev
cd apps/web && npm run test                    # Vitest
```
Baseline: **327 backend + 74 frontend tests pass** · 148 endpoints · 46 tables · 36 migrations · 33 web routes.

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
**Full as-built spec → `docs/architecture/architecture-org-tree.md §12`**; POS/roles detail → memory `roles-reference` +
`pos-mvp`; vouchers → `docs/architecture/architecture-vouchers.md`. **Critical invariants / traps (do NOT violate):**
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

## Vouchers (LOCKED 2026-06-05 → `docs/architecture/architecture-vouchers.md`)
**Shared Voucher core, two issuers, one cashier redemption.** Litmus: *earned, always-on, everyone* →
**loyalty** issuer; *granted to a trigger/segment* → **campaign** issuer — both redeemed the same way.
Scope = a node, reach = its subtree (`scope_node_id`; `merchant_id` = funding tenant). Tiers 1–2 BUILT;
tier 3 (cross-merchant = coalition + split-settlement M2) DEFERRED.

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
- **NO drive-by .md files (LOCKED 2026-06-12).** Never create a new .md unless (a) the user asked for
  it, or (b) it's a genuinely new domain with no existing home — and then REGISTER it in the same turn
  (`docs/README.md` status row for repo docs; `MEMORY.md` line for memories). Default = update the
  existing home: decision → `docs/decisions.md` · session narrative → `SESSION_NOTES.md` (the only
  session log) · design detail → the existing `docs/architecture/*.md` · plans/scopes → the doc
  they extend · context/preference → an existing memory topic file. An unindexed file is invisible
  next session — memory debt, not memory.
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
  Full design + Phase 1/2/3 → `docs/architecture/reporting-timezone.md`.

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
  - `owner@malaysiaboleh.sg` → **Malaysia Boleh!** foodcourt (FSG enterprise demo: Fei Siong Group → Malaysia
    Boleh! tenant → 6 Malaysian stalls w/ real menus). Seed: `python -m app.seed_fei_siong` → [[fsg-enterprise]].
  - Durable via the ensure-script: `python -m app.seed_demo_merchants` (idempotent; rebuilds both
    groups + storefronts + these 3 logins with fixed node ids → stable QR tokens). Run after a data wipe.
- Customer QR: scan tokens are the live storefronts' QR (see each Storefront's *Tables & QR*); OTP phone `+6580000000` (DEBUG returns the code).

## Persistent memory (tiered, LOCKED 2026-06-12 — memory `memory-lifecycle`; ENFORCE these every session)
**One home per kind of fact — write it the moment it exists, in that home, nowhere else:**
- **Decision firmed** ("locked"/"agreed"/overruled) → a `docs/decisions.md` row **in the same turn**;
  mark overruled rows SUPERSEDED. The register outranks all other prose.
- **Session history** → `docs/SESSION_NOTES.md` is **THE ONLY session log** (newest-first; each entry
  carries a Dense-record line). The old build-state "Round" entries are RETIRED — never write one;
  round narratives R1–R43 live in `build-state-archive` (deep history only).
- **Pending work / KIV** → the backlog in memory `build-state.md` (STATE only — no narratives).
- **Taste/preferences/context** → the matching memory topic file (`MEMORY.md` index); **one file per
  domain, merge aggressively** — no new .md without an absorb-check + same-turn registration (the
  no-drive-by rule in Conventions & traps).
- **This file** = constitution: invariants/traps/pointers only, keep ≤~2,300 words.
- Lifecycle: `/my-catchup` at session start; `/my-wrapup` to close — wrapup writes ONE SESSION_NOTES
  entry, then consolidates (reconcile backlog · sweep decisions · promote lessons · expire superseded).
- Memory dir: `~/.claude/projects/-Volumes-Data-Drive-Coding-multi-agent-FB-Group/memory/`.
- Project skills in `.claude/skills/`: `/my-architect`, `/my-tester`, `/my-security-audit`, `/my-dba`,
  `/my-ops`, `/my-diagnose`, `/my-bizdev`, `/my-uiux` (advisors) + `/my-catchup`, `/my-wrapup`,
  `/my-memory-heal` (lifecycle — audit every .md vs reality, fix drift, shrink the estate).

## How the user works (Founder Mode)
~2-person team + Claude Code. Prioritize speed, working+tested software, revenue/adoption — while keeping
strong security/testing/architecture standards. Be decisive; prefer prose planning over multiple-choice
prompts. Don't claim completion without passing tests + proof of the demo flow.
