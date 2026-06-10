# CIP (FB Group) — Session Notes

> Session journal started 2026-06-08. Earlier history (Rounds R1–R39+) lives in the
> memory `build-state.md`; notes here begin from this date forward — past sessions are not backfilled.
> Dense, AI/catchup-facing history stays in `build-state.md`; this file is the at-a-glance human journal.

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
- **3-module refactor — Phase A (A1–A6) shipped** (`docs/architecture-3-modules.md`): three independently
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
