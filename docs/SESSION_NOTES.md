# CIP (FB Group) — Session Notes

> Session journal started 2026-06-08. Earlier history (Rounds R1–R39+) lives in the
> memory `build-state.md`; notes here begin from this date forward — past sessions are not backfilled.
> Dense, AI/catchup-facing history stays in `build-state.md`; this file is the at-a-glance human journal.

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
