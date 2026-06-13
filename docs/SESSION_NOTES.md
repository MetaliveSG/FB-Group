# CIP (FB Group) — Session Notes

> THE single session log (decided 2026-06-12; the old dual-log build-state "Round" entries are
> retired — round narratives R1–R43 live in the memory `build-state-archive`). Newest first; each
> entry: What changed · Decisions · Dense record (commits/migrations/counts/verification + LESSONs) ·
> Still open. Journal started 2026-06-08; earlier sessions are not backfilled.

---

# Session — 2026-06-13 — FSG payments + phase-① counter flow (design, no code)

## What changed
- **FSG roadmap RE-SEQUENCED** (`edfbe81`): ① loyalty + CRM first → ② wallet/credit-card at the
  EXISTING uPOS counters → ③ online ordering last. Propagated to `payments.md` build slices +
  build-state direction + the kpmg memory.
- **`architecture/payments.md` heavily extended** — the counter rail spec:
  - **§7b scan-at-tender rail** (`cd1525c`,`227932e`): customer-presented — cashier bills in uPOS,
    diner shows a one-time CIP QR, **cashier scans → on txn submit uPOS POSTs `/tender/scan` →
    CIP validates+redeems atomically → uPOS deducts → shows balance**. ONE rail serves vouchers
    (①) and wallet (②). Engine = `tender_intents` + token service + idempotency by `txn_id`.
  - **Item-level capture + voucher-at-counter** (`77abcc5`): §8 webhook (items + OPTIONS like
    chilli/dry-soup) is the intelligence artery; vouchers redeem by riding the payment.
  - **Voucher state machine** (`83d589e`): redeem-on-scan, atomic; armed≠redeemed; sequential
    unlock fires at scan-approval.
  - **Offline/degraded design** (`aa3921e`): store-and-forward MANDATED of uPOS; signed-QR
    break-glass; coins provisional-not-spendable until confirmed; expiry 72h from reconnect.
- **`docs/flow-phase1.md` created** (renamed from flow-mindmap) — the phase-① flow as: 30-second
  board+CTO pitch · 14-step vertical flow (ASCII + Mermaid) · **Flow B** receipt-discovery door ·
  **Flow C** connection-down · engineer sequence diagram. `.vscode` recommends the Mermaid extension.

## Decisions (all register rows, dated 2026-06-12/13)
- FSG re-sequenced (loyalty easiest to roll out, captures data first).
- Item-level counter capture (what/where/how-much + options) is mandatory — feeds CRM/AI.
- Customer-presented scan-at-tender; the till owns the bill (diner never keys the amount).
- Voucher = redeem-on-scan atomic; sequential welcome-pack unlock.
- Offline: store-and-forward mandated + signed-QR break-glass; coins provisional; expiry from reconnect.
- Flow B: receipt-QR scan earns the meal's coins + welcome pack for a first-timer.

## Dense record
- Commits `edfbe81`…`5449fd3` (18) · migrations: NONE · counts UNCHANGED (148 endpoints · 46 tables ·
  36 migrations · 327+74 tests · 33 routes) · **docs/design only, zero code** · verified: decisions
  register + flow doc + payments spec mutually consistent (heal-style grep, no stale paths).
- PRINCIPLE worth keeping: **value-state is realtime + server-side (redeem/debit/mint commit in CIP
  at scan time); evidence-data is async (the uPOS webhook may lag — enriches + confirms later).**
  Authorization never waits on, or trusts, the late data.

## Still open / next session
- Build phase ①: CIP-side token service + `/tender/scan` + `tender_intents` + sequential unlock
  (uPOS-independent, can start now); FSG sends uPOS the §8 handout (6 Qs — Q1/Q1b/Q5 gate phase ①).
- 🔀 parked routes in flow-phase1.md (wallet rail detail, online ordering, multi-voucher, M2 funding).
- Earn economics (100 coins/$ gross · 100 coins = $1 food-only · min-spend $3) = tenant config — confirm at build.
- Untracked `artifacts/` benchmark dirs + `showcase/beat3/` — commit vs gitignore (carried KIV).

---

# Session — 2026-06-12 (pm) — persistent-memory system

## What changed
- **Decision register** `docs/decisions.md` — 28 rows backfilled (2026-05-26→today) with
  LOCKED/AGREED/DEFERRED/SUPERSEDED statuses + supersedes chains; capture rule in CLAUDE.md =
  append the row in the same turn a decision is firmed.
- **Tiered memory lifecycle** enforced in CLAUDE.md §Persistent memory (one home per kind of fact);
  CLAUDE.md slimmed 2,911→~2,330 words (scan-domains/KDS/service-options narratives → docs).
- **docs/ foldered**: root = 4 living files (README · decisions · delivery-report · SESSION_NOTES) +
  `architecture/` · `reference/` · `business/` · `archive/`; new `docs/README.md` status map;
  39 files' references rewritten, grep-verified.
- **Consolidations**: 4 payments docs → `architecture/payments.md`; 3 UI/UX memories →
  `design-language.md`; 4 thin memories folded into user-prefs/build-state; `memory-lifecycle.md`
  folded into CLAUDE.md; dual session log → THIS file only; build-state → state/backlog only
  (6,133→938 words). Memory dir 43→37 files.
- **Skills**: `/my-uiux` refreshed (stale demo creds/OTP, tokens-built, Lucide-adopted, theme-cascade
  + i18n context) + reads `design-language` first; `/my-wrapup` = single log + consolidate;
  `/my-catchup` reads register + SESSION_NOTES; **NEW `/my-memory-heal`** — audits every .md vs
  reality; first pass ran: 31 findings → 24 auto-healed (stale counts in poc-demo/my-tester/
  my-architect, legacy QR tokens presented as live in my-ops/my-tester, PR-flow claim in catchup).

## Decisions
- All registered same-turn (rows dated 2026-06-12): memory lifecycle · no-drive-by .md files ·
  docs foldered · ONE session log. Plus user prefs recorded: one file per domain, merge aggressively.

## Dense record
- Commits `31f1c02`…`a465984`+fold (13, all pushed incrementally) · migrations: none · counts
  unchanged: 148 endpoints · 46 tables · 36 migrations · 327+74 tests · 33 routes · verified:
  heal-pass grep sweeps = zero stale paths, zero dead wikilinks, zero registration orphans.
- LESSON: a memory file can be indexed, accurate, AND pointless — first test before creating one is
  "is this already in the always-loaded constitution?"
- LESSON: hardcoded counts in skills rot — point at the CLAUDE.md baseline/artifacts instead.

## Still open / next session
- HitPay real payment (KPMG pilot critical path) → `docs/architecture/payments.md` slice 1.
- Carry FSG red/editorial art direction to the MB home; UI-string/currency sweep (incremental).
- CLAUDE.md sits ~105 words over its 2,300 budget (remaining content is load-bearing — revisit only
  if it grows). Untracked `artifacts/` benchmark dirs + `showcase/beat3/` — commit or gitignore, TBD.

---

# Session — 2026-06-12

## What changed
- **i18n/l10n foundation** (`packages/i18n`, migration `k5l6i18n`): language/currency/timezone as **3
  decoupled axes** (person/settlement/place, Grab-validated). `LocaleProvider` + `useT` + `formatMoney`
  (zero-decimal-currency safe); `ENABLED_LOCALES` gates the switcher (limited to **English + Singlish**
  for now); menu `translations` JSON slot (author-once/present-many, fallback-to-canonical);
  `customers.locale`. Backend `app/services/i18n.py` locale resolver (override→tenant→Accept-Language).
- **Brand-theme cascade** (migration `j4k5theme`, `org_nodes.theme` JSON): per-tenant brand kit
  (`primary`/`accent`/`logo`/`hero`/`tagline` + `enterprise_*` showcase fields) resolved
  nearest-ancestor-wins, surfaced in the QR context. `_THEME_KEYS` in `boundaries.py` is the single gate.
- **Malaysia Boleh! foodcourt aesthetic**: content-rich home (Chagee/Luckin-grade) — branded hero
  slideshow, segment filter, recommended scroll, **all-stalls directory**, mascot + animated steam,
  "Get to know FSG" map with blinking outlet dots; **real stall signboards** (migration `l6m7signboard`,
  `menus.signboard_url`) + free-licensed dish photos. +3 Jurong Point stalls (now 9).
- **FSG enterprise showcase** at `/t/node/fsg` (`EnterpriseHome.tsx` + `/awards` page): watercolour
  editorial hero, auto-scroll brands, "Our story" slideshow→timeline, CSR, awards banner — all
  theme-cascade-driven from the FSG enterprise node.
- **Richer "All stalls" rows** (final polish): signboard + name + "from S$X" + cuisine + personality tag
  + a real dish-preview line. Backend `catalog.menu_preview()`; `StallRef` += `price_from`/`top_items`.
  Re-trimmed signboards 12%→5% margin + landscape 76×56 tile + white Recommended cards (fixes
  "logos small / too much white border"). `stallTag` "Bak Kut Teh"→drinks-"teh" mistag fixed.

## Decisions
- **Three axes stay decoupled** — language ≠ currency ≠ timezone (a diner's language never changes the
  money or the time). Critical to lay before the FSG menu is authored (retrofitting translations later = pain).
- **Signboard look needs THREE fixes together** — re-trim art margin + landscape row tile + white cards.
  Square `contain` tiles letterbox wide text signs into a thin band → "small logo". (memory `signboard-row-art-fix`)
- **FSG seed is already idempotent** — `_seed_stall_menu` refreshes signboard/cuisine/logo/image on every run;
  the earlier "didn't update" was the **api container running stale baked code** (no source bind-mount).
  Lesson: edit seed → **rebuild api** → then `exec` the seed.

## Dense record
- Commits `7cd7f87`…`b24f0ec` (~33) · migrations: `k5l6i18n`, `j4k5theme`, `l6m7signboard` ·
  counts: 148 endpoints · 46 tables · 36 migrations · 327+74 tests · 33 routes · verified:
  Playwright @390px on live Postgres, pytest/vitest green, openapi 148 ops.
- LESSON: api container has NO source bind-mount — edit seed → `docker-compose build api` → then exec.
- LESSON: art "small in a white border" = stacked PNG margin + tile padding + aspect mismatch — fix all.

## Still open / next session
- Carry the red/editorial art direction from the FSG showcase to the MB home for consistency.
- HitPay real payment (KPMG foodcourt pilot critical-path).
- Full UI-string + currency-display sweep is INCREMENTAL (foundation laid, not every string localized).
- Menu-page grid redesign (deferred); crisper FSG award badges; Facebook dish photos (login-gated).

---

# Session — 2026-06-11

## What changed
- **Member-tree table redesign:** the 3 module flags went **3-state → binary + parent-gated**
  (`effective = AND of own-flags up the path`; a child can't override a parent's OFF). Added **`mod_wallet`**
  as a 4th toggle (binary, parent-gated, gated by Table-QR). Rebuilt the **`/platform` Merchant Directory as a
  tree-grid** with inline capability toggles, name=Enter, "N inside"=walk-down, QR-Menu gated on Table-QR.
- **KDS — kitchen display** (`/kds`): paid-order queue + a separate **`fulfilment_status`**
  (queued→preparing→ready→collected), "mark ready" flow, launched from the tree-grid + merchant orders.
- **Two-axis service options (fulfilment):** dining context (`order_type` dine_in|takeaway) × **hand-off**
  (`hand_off` self_pickup|served). Storefront configures the enabled SET (cascade); diner picks per order.
  **SEA-first default = Self-Service + Takeaway.** Drawer config = Dine-in [Self-Service|Served] + Takeaway
  on/off. KDS shows **🍽 plate / 📦 package**. Studied Toast/Square/Olo to get the model right.
- **Customer ready-to-collect notification:** full-screen **popup** (once per order, swinging 🔔) + **sticky
  banner** + **Orders-tab badge** — app-wide (CustomerTabBar polls 6s; auto-closes on collected). My Orders
  shows the pick-up journey + a **✓ Paid** cue. Order# = 8 chars with a **forced 3-digit numeric tail**.
- **Auth:** customer access token → **1 week** (staff stay 8h); on expiry → "Session expired" → re-login →
  **resume at the pay screen**.
- **Fixes:** wallet model-drift (NOT-NULL cols); **QR codes printed blank** (CSS specificity); KDS leaked the
  diner's **phone** → now shows the order number (PII fix). Recovered the stack from a **Docker disk-full**
  Postgres crash (WAL-recovered, data intact; pruned 35GB→4.9GB).

## Decisions
- **Scan domains** = per-tenant CIP subdomains **`{slug}.mycip.io`** (apex `mycip.io`); QR host from per-tenant
  config, never `window.location.origin`. BYO custom domains = Tier-3, deferred.
- **KDS auth** = station binding (private per-outlet token), **no login / no password**; gate on Table-QR.
- **Fulfilment = two orthogonal axes**, not one mode (Toast/Olo bundle dine-in=table-service; CIP decouples →
  the SEA foodcourt "eat-in self-collect" — an M4 moat). The **"ready" alert keys off `self_pickup`, not dine-in**.
- **Per-stall service options in a foodcourt = NOT needed, deferred into M2** — foodcourt orders attribute to the
  venue outlet, so per-stall can't take effect until M2 stall-outlet attribution; real foodcourts are uniform
  self-service → venue cascade default is correct.
- **Service charge SHOULD key off `hand_off==served`** (not `order_type==dine_in`) so foodcourt self-collect
  isn't wrongly charged — noted, **parked** (one-liner).

## Still open / next session
- **Real-time push** for ready-to-collect (SSE/WebSocket + Web Push) — today in-app poll ≤6s (KIV).
- **HitPay** real payment (mock→real on the existing `payment_providers` seam); wallet connector + checkout-as-tender.
- Fulfilment polish: **`pickup_number`**, conditional table (hide for self-pickup-only), **service-charge fix**.
- Scan-domain **`slug` resolver** (swap QR off `window.location.origin`); KDS **station-token** hardening.
- Webapp aesthetics pass; turn on real AI for the demo.

---

# Session — 2026-06-08

## What changed
- **Product named: Customer Intelligence Platform (CIP)** — CRM · AI · Payment · Ordering · Rewards.
  Added the product section + pitch + **Luckin Coffee growth model** to `CLAUDE.md`, and grounded the
  member-tree **glossary** against actual code (no invented terms: "tenant" = settlement boundary,
  "Enterprise" = a concept/legacy label, NOT a built node kind).
- **3-module refactor — Phase A (A1–A6) shipped** (`docs/architecture/architecture-3-modules.md`): three independently
  toggleable modules — **Table QR · Intelligence · POS** — on a shared core.
  - **A1** per-node 3-state module flags (`mod_rewards`/`mod_qr_ordering`/`mod_pos`, nullable=inherit) on
    `org_nodes` + cascade resolver `boundaries.resolve_modules()` (nearest explicit ancestor wins →
    `Merchant.settings` fallback). Migration `b6c7modflags`.
  - **A2** enforcement: ordering + earn gates (`orders.py`), QR context (`qr.py`), and POS PIN-login
    (`auth/service.py`) now resolve via the cascade. `pos_enabled` default flipped **True** (POS is built).
  - **A3** per-node toggle UI in `NodeDetailDrawer` + `GET/PUT /org/nodes/{id}/modules`.
  - **A4** adaptive nav: dashboard sidebar (`merchantNav.ts` + `MerchantSidebar`) and the customer tab bar
    (`CustomerTabBar`) **show/hide on module toggle** — the explicit acceptance criterion.
  - **A6** POS nav section + **"Customer Engagement" → "Intelligence"** rename everywhere; segmented-radio
    toggle UX (replacing the cramped dropdown).
- **RBAC cleanup**: web role **`staff` → `viewer`** (view all except reports), **`finance`** = reports only.
  **Consolidated the merchant Team page onto the node model**; **deleted dead legacy `/admin/users`** path
  (route + schema). Web Team listing now filters to **web-palette roles only** (excludes POS
  cashier/supervisor + `@pos.local` operators) — fixed a 500/"NetworkError" from `EmailStr` on POS emails.
- **POS pages**: moved Staff & PINs and the Receipt header out of Settings into a **Point of Sale** nav
  section (`merchant/pos-staff`, `merchant/pos-settings`, `PosReceiptCard`).
- **Seed fix**: demo merchants had empty games → `seed_demo_merchants._ensure_demo_games` now seeds a
  working wheel + 3×3 jackpot (idempotent) per tenant; re-ran live (`games_seeded: 2`).
- **Skills revised**: `/my-uiux` (control-selection decision table — 3–4 mutually-exclusive options →
  radio/segmented, never a dropdown), `/my-wrapup` (this `SESSION_NOTES.md` practice + direct-to-main fix),
  `/my-catchup` (read `docs-index`; fixed stale git/creds).
- **Workflow**: dropped PR flow — **commit directly to `main`** (branch protection removed).

## Decisions
- **Modules cascade like RBAC** — 3-state per node (inherit/on/off), resolved on the spine, fallback to
  tenant `Merchant.settings`. Keeps future phases additive (Foundation Contract #7: everything behind flags).
- **POS default ON** — it's built; only Table QR / Intelligence are genuinely optional-by-merchant.
- **Cashier/Supervisor are POS-only** (PIN, `@pos.local`) and must never appear in the web Team list —
  segregated login surfaces, enforced at the listing query, not just the UI.
- **CIP + Luckin model** is the north-star narrative: capture identity → segment → campaign → win-back →
  referral loop (referral still the top unbuilt growth lever).

## Still open / next session
- **Webapp aesthetics touch-up** (KIV) — polish pass via `/my-uiux`; turn on real AI for the demo.
- **3-module Phase B–F**: B `record_sale()` hub → C earn-weld break → D LAND counter-QR → E KDS → F referral loop.
- **Games per-storefront toggle + per-SF spin-cost** (advised, not built — node cascade like module flags).
- **Voucher third-party-POS redemption** model (A/B/C) still undecided.
