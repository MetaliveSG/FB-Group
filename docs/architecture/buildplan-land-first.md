# Build Plan — LAND-first (Loyalty-only SKU)

**Status:** DRAFT for approval (2026-06-07). Plan-first, not started. Ships the **loyalty-only**
counter-QR product (no POS, no table-ordering) — the "LAND" tier of the 3-module ADR
(`docs/architecture/architecture-3-modules.md`). Grounded against the code on 2026-06-07 (see §Grounding).

## Goal / Definition of Done
A merchant with **no POS and no table-ordering** runs a rewards program: hang a **counter join-QR** →
customer enrolls (OTP) → **the existing 10×$1 welcome voucher is issued on signup** → customer redeems a
voucher at the counter via a **web Redemption Centre** (staff enters/scans the voucher code → validate →
mark used; merchant applies the discount on their own till). Console shows **only Intelligence**;
customer app shows **only Rewards**. Demoable end-to-end, tests green, verified on Postgres.

## Grounding — verified against code (2026-06-07)
What already EXISTS (do **not** rebuild):
- **Welcome voucher (the LAND earn) — BUILT.** `services/vouchers.py::issue_welcome_pack` mints the pack
  from `Merchant.settings["welcome_voucher"]` (`{enabled,count,value,per_period,valid_days,name,scope_node_id}`,
  e.g. 10×$1 one/day), **idempotent per (customer, merchant)**.
- **Welcome fires on signup — BUILT.** `routes/auth.py::_issue_welcome` is called by `/customer/register`,
  `/customer/otp/verify`, `/customer/sso` whenever **`consent_merchant_id`** is supplied (best-effort,
  post-commit). → Enrollment for LAND needs no new auth endpoint; it needs a front door that drives the
  existing OTP flow with `consent_merchant_id` = the join node's tenant merchant.
- **No-order redeem — BUILT.** `services/vouchers.py::redeem_voucher(order=None)` validates + marks the
  voucher used without an order (min-spend & scope checks are skipped when there's no order/node).
  `POST /vouchers/{code}/redeem` accepts `{merchant_id}` with **no `order_id`**, gated `order.manage`
  (`_merchant_for` falls back to `resolve_merchant(scope)`).
- **Voucher preview + diner lookup — BUILT.** `GET /vouchers/{code}` (dry-run validate) and
  `GET /vouchers/diner/{customer_id}` (a member's ISSUED vouchers, gated `order.view`).
- **Welcome vouchers have `min_spend=0`** (`issue_welcome_pack` → `issue_vouchers` defaults) → no-order
  redeem of a welcome voucher is fully valid as-is.
- **Sidebar gating machinery — BUILT.** `components/MerchantSidebar.tsx` has `perm`/`flag`/`navVisible()`
  + auto-hides empty sections; today's only dynamic flag is `pipeline_enabled`.

What is NOT built (the real work):
- A **standalone "join rewards" entry** decoupled from ordering (no `/join` route today).
- A **web Redemption Centre UI** (the endpoints exist; there's no merchant page that uses them off-order).
- **Module flags as 3 modules** (today flat `qr_ordering_enabled`/`rewards_enabled` on `Merchant.settings`).
- The **welcome_voucher config is not in `seed_demo_merchants`** (live-only → lost on a data wipe).
- **Member-identity QR** (only needed if redemption identifies by scanning the *person* — see L2 decision).

## Explicitly OUT of scope (deferred)
- `record_sale()` event hub + `loyalty event` abstraction (ADR steps 1–2 — the post-LAND refactor).
- **Stamp / visit-based / check-in earn** — dropped; the welcome voucher is the earn. (No new earn mechanic.)
- Full **tree-cascaded** module flags (LAND uses a tenant-level flag; cascade is the later refactor).
- Table QR / POS modules, KDS, referral, keep-your-POS connectors, receipt OCR.
- Keyed-amount earn (the fraud surface) — not built.

---

## Phases (suite-green each)

### L1 — Counter-QR join front door  ·  ~1.5 days
The genuine new entry. Backend enrollment is REUSED.
- **NEW** node→join resolve: a thin resolver returning `{merchant_id (tenant), display_name}` for a join
  token (reuse the existing node/QR resolution; the join token identifies the storefront/tenant node).
- **NEW** web `/join/[token]`: mobile-first landing — brand header → "Join rewards" → drives the existing
  **`POST /auth/customer/otp/request` + `/otp/verify`** with `consent_merchant_id` = the resolved tenant →
  the welcome pack auto-issues → enrolled screen (their voucher(s) + code).
- **NEW** merchant "Rewards Join QR" surface (print/download), analogous to `/merchant/tables`, under
  Engagement.
- **REUSE** `_issue_welcome` (no auth change).
- Tests: join → welcome pack issued (count/value per config); idempotent re-join; OTP path. (`test_join.py`)

### L2 — Redemption Centre (web)  ·  ~1.5 days
Mostly UI over existing endpoints.
- **NEW** web `/merchant/redeem` (Engagement, gated `order.manage`): staff enters/scans a **voucher code**
  → `GET /vouchers/{code}` preview (confirm value) → `POST /vouchers/{code}/redeem` with `{merchant_id}`,
  **no order** → marks used; show "✓ $X off — apply on your till".
- **EXTEND (small)** redeem route to write an **audit log** row `{staff, voucher, merchant}` for the manual
  path.
- *(Optional, only when non-zero-min-spend vouchers exist later)* accept a keyed `amount` for min-spend +
  a redeeming node id for scope. **Skip for v1** (welcome `min_spend=0`).
- **DECISION (see below)** v1 identifies by **voucher code** (customer shows code / voucher-QR). Member-QR
  identification is L2b/optional.
- Tests: manual redeem marks used; already-used → 409; wrong-tenant → 404; audit row written.
  (`test_redeem_manual.py`)

### L2b — Voucher/member QR (OPTIONAL, pending decision)  ·  ~0.5–1 day
- If scanning is wanted: render a **QR of the voucher_code** in the customer Rewards tab (`qrcode.react`)
  so staff can scan instead of type; and/or a **member-identity QR** → `GET /vouchers/diner/{customer_id}`
  to list all their vouchers. Defer unless the demo needs scanning.

### L3 — Module flag + adaptive nav (tenant-level slice)  ·  ~1.5 days
- **EXTEND** backend: 3 module flags (`engagement`/`table_qr`/`pos`) on `Merchant.settings` (tenant-level
  for now) + return them from the nav-flags endpoint. (Tree-cascade onto `org_nodes` = the later refactor.)
- **EXTEND** `MerchantSidebar.tsx`: add `module` per `NavItem`, regroup sections by module (ADR §7.4/§7.6),
  hide off-module sections (machinery exists).
- **EXTEND** `CustomerTabBar.tsx`: Engagement-only → `[Rewards][Me]` (no Menu).
- **EXTEND** off-module endpoints → clean disabled code (not 500).
- Tests: loyalty-only merchant → only Engagement nav; ordering endpoints disabled; vitest sidebar/tabbar.
  (extend `test_module_gating.py`)

### L4 — Seed + proof  ·  ~0.5 day
- **EXTEND** `seed_demo_merchants`: write the `welcome_voucher` config (the known pending gap) + a
  loyalty-only demo merchant (Engagement on, Table QR + POS off).
- E2E proof: **join → 10×$1 issued → redeem one at the Redemption Centre**; capture to
  `artifacts/land-proof/`.
- Update `delivery-report.md` + memory `build-state`.

---

## Estimate
~**5 days** (L1+L2+L3+L4; L2b optional). Critical path **L1 → L2** (join → redeem). New code concentrates
in the **join landing** and the **Redemption Centre UI**; the rest reuses verified endpoints.

## Risks
- **Don't touch the earn hot path.** LAND adds no earn mechanic; `loyalty/engine.py` stays untouched.
- **Tenant-level flag is interim** — the real model is the `org_nodes` cascade (ADR §7). Avoid letting the
  interim flag calcify into a second flag system; it's a deliberate stepping-stone.
- **Scope/min-spend skipped on no-order redeem** is fine for welcome vouchers (`min_spend=0`, tenant-wide).
  Note it before enabling non-zero-min-spend or node-scoped vouchers in a loyalty-only merchant.

## Decisions to confirm before building
1. **Redeem identification v1:** voucher **code** (type/scan the voucher — simplest, my lean) vs
   **member QR** (scan the person → pick a voucher). Decides whether L2b is on the path.
2. **Join token:** a new `/join/{token}` resolve vs. reuse an existing node/QR resolve (implementation
   detail; will resolve during L1).

---
**Related:** `docs/architecture/architecture-3-modules.md` (the ADR) · [[three-modules-adr]] · [[voucher-redemption-design]]
· [[gtm-pos-agnostic-capture]] · [[roadmap-mvp-foundation]].
