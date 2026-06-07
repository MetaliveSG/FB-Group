# Three modules on one core — architecture decision (decided 2026-06-07)

**Status:** AGREED, plan-first (not yet built — refactor + 2 small builds). The decision: split the
product into **three independently toggleable modules — Table QR · Customer Engagement · POS — sitting
on one always-on shared core**, communicating through a single sale-event seam so each module enables,
disables, and functions independently. Grounded in the observed SG market reality (rewards programs run
*decoupled* from the POS — counter-QR sign-up of a different brand) and in the Foundation Contract
guarantees #6 (one `record_sale()` core) and #7 (everything behind capability flags).

This supersedes the ad-hoc per-merchant feature flags (`qr_ordering_enabled`, `rewards_enabled`, …) by
rationalising them into exactly **three top-level module flags** with defined graceful-degradation rules.

---

## 1. Why modularise (the driver)

In the SG F&B market, loyalty/rewards is overwhelmingly sold and run **separately from the POS** — the
"join our rewards" QR you see hung at the cashier counter is a third-party overlay (Perx, Fave, stamp
apps), not a POS feature. Merchants and customers are already trained to accept rewards as a parallel
layer. So the product must let a merchant adopt **any one module alone** (most importantly: loyalty-only,
no POS, no ordering) and **compose them** when more than one is on.

Modularity is therefore not just hygiene — **it is the packaging and pricing model** (see §6) and the
launch strategy (land on the cheap module, expand into the others).

## 2. The cut — 3 modules on 1 shared core

The three modules are **not peers**. There is an always-on **shared core** beneath them; the modules sit
on top. The core is never a toggle.

```
┌──────────────────────────────────────────────────────────┐
│  SHARED CORE  (always on — NOT a module / not toggleable)  │
│  • Member tree / tenant spine + capability flags           │
│  • Identity (customers + staff/PIN auth)                    │
│  • Catalog (menu / items / prices)     ← used by QR + POS   │
│  • Payment / checkout                  ← used by QR + POS   │
│  • Customer Directory (identity + their orders/spend, raw)  │
│  • record_sale() → Transaction ledger  ← THE HUB / SEAM     │
└──────────────────────────────────────────────────────────┘
        ▲                    ▲                     ▲
 ┌──────┴─────┐     ┌────────┴────────┐     ┌──────┴──────┐
 │  TABLE QR  │     │   CUSTOMER       │     │     POS     │
 │  (order)   │     │   ENGAGEMENT     │     │  (cashier)  │
 └────────────┘     └─────────────────┘     └─────────────┘
  SALE PRODUCER      SALE CONSUMER            SALE PRODUCER
  emits sale-event   + RULE PUBLISHER         emits sale-event
                     consumes events+visits
                     publishes rules
```

### Module roster

| Module | Customer-facing | Merchant-facing | Role on the seam |
|---|---|---|---|
| **Table QR** | scan-to-order, menu browse, cart, checkout | KDS / order-display (fulfil) | **sale producer** + rule consumer |
| **Customer Engagement** (was "Rewards") | join QR, earn (stamp/points), redeem, vouchers, coalition, games | **CRM** (profiles, RFM, segments, tags, notes, churn) · **campaigns/marketing** (WhatsApp, audiences, ROI) · **win-back** · AI insights · loyalty/earn config | **sale consumer** + **rule publisher** |
| **POS** | — | cashier ring, payment, receipt, void, diner-attach, voucher redeem | **sale producer** + rule consumer |

> **Naming:** the module formerly called "Rewards" is renamed **Customer Engagement** — "Rewards" undersold
> its merchant-facing half (CRM + campaigns + marketing), which is where most of the SaaS value and pricing
> sits. Loyalty is the *capture hook*; CRM/campaign/marketing is the *monetisation of the captured asset*.
> They are one module with two faces (see §4).

## 3. The principle that makes modules independent — producers vs. consumer

**Table QR and POS are sale _producers_; Customer Engagement is a sale _consumer_. Modules never call each
other directly — they communicate only through the `record_sale()` event seam.**

- A producer rings a sale → `record_sale()` → records a `Transaction` **and emits a sale event**.
- Customer Engagement **subscribes** to sale events (earn on verified spend) — but **also has its own
  inputs** (join, check-in/stamp, manual redeem, receipt), so it runs with **zero producers enabled**.

The seam is **bidirectional** — Engagement also *publishes rules* that producers consume at sale time:

```
Customer Engagement  ──publishes──►  earn rules · vouchers · promotions · audiences
        ▲                                          │
        │ consumes                                 ▼  consumed at checkout by
 sale events + check-ins   ◄──────emits──────  Table QR / POS
```

This symmetry is *why* CRM/marketing stays inside Engagement rather than leaking into the order flow:
producers don't know how points are computed or which promo applies — they just call the seam and apply
the rules the seam returns.

## 4. Where CRM / campaigns / marketing live (and why not a 4th module)

**Inside Customer Engagement** — they are its merchant-facing half. They are **not** a separate module
because they cannot function or be sold without the customer database that loyalty/capture creates:

- a loyalty program with no merchant dashboard is useless;
- a CRM with no capture mechanism is empty.

Loyalty **captures** the customer; CRM/campaign/marketing **monetises** the captured asset. Same coin,
one module.

A thin slice *does* belong in the shared core — a **minimal Customer Directory** (identity + their
orders/spend), because any producer with an attached diner creates a customer record and a sale even when
Engagement is off. That bare record is raw data, always present. The **rich** layer (segmentation, RFM,
tags, campaigns, AI) is the Engagement module on top of it.

**Sub-capability, not sub-module:** a merchant may run Engagement in **"marketing-only, no points"** mode
(capture via join QR → CRM → WhatsApp blasts, give no loyalty rewards). That is the loyalty-earn
sub-feature toggled off *within* Engagement — still one top-level module.

## 5. Independence rules (graceful degradation)

Each module must behave sensibly when the others are off. These rules are the contract:

| Configuration | Behaviour |
|---|---|
| **Table QR on, POS off** | orders fulfil via the **KDS / order-display** screen (staff reads + marks ready); no cashier required |
| **Table QR on, Engagement off** | ordering works; mints no points; basic Customer Directory record still created |
| **POS on, Engagement off** | cashier sells + takes payment; no loyalty UI; basic Customer Directory record still created |
| **Engagement on, both producers off** | **counter-QR join + check-in/stamp + manual redeem** (no sale data — acceptable for this tier) |
| **Engagement on + any producer on** | verified **sale events auto-earn** on real spend; manual/check-in is the fallback |
| **any module off** | its endpoints return a clean disabled response (e.g. `409`/`403` with a module-disabled code), never a 500; its nav hides |

## 6. The enable/disable matrix = the product SKUs

Same codebase, seven sellable configurations, priced per module — land-and-expand built into the
architecture:

| Table QR | Engagement | POS | = Product / SKU |
|:---:|:---:|:---:|---|
| – | ✅ | – | **Loyalty-only** — counter-QR, the Perx competitor (**the LAND**) |
| ✅ | ✅ | – | Self-order + earn — café QR ordering with loyalty |
| – | ✅ | ✅ | Cashier + loyalty — counter business on our till |
| ✅ | ✅ | ✅ | Full stack (**the EXPAND**) |
| ✅ | – | – | Digital menu / order only (no loyalty) |
| – | – | ✅ | Standalone cashier POS |
| ✅ | – | ✅ | Order + cashier, no loyalty |

**Pricing implication:** Engagement-only is the cheap/free **land** tier (no GMV visibility → flat
subscription). Adding a producer (Table QR or POS) gives GMV visibility → unlocks per-transaction /
coalition revenue (the **expand**). The capture mode you sell is your revenue model in disguise.

## 7. Tree-level module flags + adaptive navigation

**Every node carries a per-module setting; it cascades down the subtree; the side menu (and the
customer-facing surfaces) render only the modules resolved ON for the current scope.** This generalises
today's per-merchant `Merchant.settings` flags onto the org spine.

### 7.1 Where the flags live + how they resolve

- A **3-state setting per module** on each node: `inherit` (default) · `on` · `off` — stored on
  `org_nodes` (the spine), alongside the boundary/`sells`/`chain_stopped` flags.
- **Resolution** = walk up the `path`; the **nearest explicit `on`/`off` wins**; platform/root default if
  none set. Same cascade machinery as flag-based RBAC (`grants_for_node`).
- A Chain set to a module `on` → every storefront in its subtree **inherits** it; a Storefront may
  **override** its own.

### 7.2 All three toggle per-storefront — participation ≠ shared data

**All three modules toggle per-storefront for their point-of-sale behaviour, cascading the same way.** The
key insight: *participation* (does this store earn/order/ring) is separate from *shared data* (the one
ledger/CRM per tenant). Only the shared data is tenant-singular — and it isn't a point-of-sale toggle
anyway, so it needs no per-store switch.

| Layer | Scope | Per-storefront toggle? |
|---|---|---|
| **Table QR** — ordering at a store | storefront | ✅ yes |
| **POS** — ringing at a store | storefront | ✅ yes |
| **Engagement — earn/redeem at a store** (participation) | storefront | ✅ **yes** |
| Engagement — the **ring** (balance ledger) + CRM + campaigns + coalition (shared data/config) | tenant | n/a — singular per tenant, not a point-of-sale switch |

So **"storefront A earns/redeems, storefront B doesn't" is fully supported with no new data model.** Both
sit on the one tenant ring; B simply doesn't participate at its till. Coins a customer earned at A stay
usable at any *participating* storefront (incl. A). The only thing that would need a bigger change is
giving B its **own separate balance/ring** — out of scope, nobody's asking.

**Cascade is uniform for all three:** a Chain toggle sets participation across its storefronts; any
storefront overrides its own. The tenant-level "ring/CRM exists" is established once at the tenant boundary
(it's where the shared data lives); per-storefront participation rides the cascade like QR and POS.

### 7.3 Nav visibility = three filters composed

A nav item (or page) shows **iff all three hold**:

> **module enabled at scope** × **user has the permission** (RBAC) × **page applies at this node tier**
> (the unified-console structural / analytics-rollup / per-tenant rule — [[unified-console-plan]])

Module flag is the *new* filter layered on top of the existing RBAC × node-tier filters.

### 7.4 Nav-group → module map (merchant console)

| Nav group | Module | Show-if |
|---|---|---|
| Dashboard · Settings · Team/Logins · Org tree | **Core (always)** | always (Org tree only at chain/operator scope) |
| Menu · Tables & QR | **Table QR** | Table QR on |
| Orders (live feed / KDS) | Table QR **or** POS | ≥1 producer on |
| CRM · Campaigns/Marketing · Loyalty config · Voucher authoring · AI Insights | **Customer Engagement** | Engagement on |
| Reports | any producer | ≥1 producer on (Engagement adds loyalty/campaign analytics) |
| POS Staff & PINs · Transactions / day-end · the `/pos` PIN app | **POS** | POS on |

### 7.5 Customer-facing surfaces adapt too

The customer app's 4-tab nav (**Menu · Rewards · Orders · Me**) adapts to the **storefront's** resolved
modules, and the *entry point* differs by module:

- **Table QR on** → table/order QR `/t/{token}` opens the menu + ordering.
- **Engagement-only** (Table QR off) → the counter **join QR** opens an enroll → stamp/rewards surface
  with **no menu**.
- **Engagement off** → no Rewards tab.

### 7.6 What the side menu looks like (agreed 2026-06-07)

Sections in `components/MerchantSidebar.tsx` regroup from functional clusters (Overview / Orders & Menu /
Growth / Admin) into **module sections**; a whole section disappears when its module is off for the scope
(the sidebar already auto-hides empty sections + has the `perm`/`flag`/`navVisible()` machinery — this just
adds a `module` tag per item + a resolved-module-set fetch per §7.1).

**Full stack (Table QR ✓ · Engagement ✓ · POS ✓):**
```
CUSTOMER ENGAGEMENT  CRM & Analytics · RFM · Campaigns · Pipeline · Loyalty & Vouchers* · AI Insights · My Tasks
ORDERING (Table QR)  Orders / KDS · Menu Editor · Tables & QR
POINT OF SALE        POS Staff & PINs · Transactions / Day-end*
REPORTS              Reports                 (shared — shows if any module has data)
ADMIN (always)       Team · Settings
```
`*` = new pages (Loyalty & Vouchers surfaces config that lives in Settings today; Transactions/Day-end not built).

**Loyalty-only — the LAND tier (Engagement ✓ · Table QR ✗ · POS ✗):** `ORDERING` + `POINT OF SALE`
sections vanish; left with `CUSTOMER ENGAGEMENT · REPORTS · ADMIN`.
**Café self-order (Table QR ✓ · Engagement ✓):** `POINT OF SALE` vanishes.
**Standalone till (POS ✓ only):** only `POINT OF SALE · REPORTS · ADMIN`; selling happens in the `/pos` app.

**Customer app (`CustomerTabBar.tsx`) adapts in parallel:**
```
Table QR ✓ + Engagement ✓ :  [ Menu ] [ Rewards ] [ Orders ] [ Me ]
Engagement-only (LAND)     :  [ Rewards ] [ Me ]            (no menu; entry = counter join-QR)
Table QR-only              :  [ Menu ] [ Orders ] [ Me ]    (no Rewards)
```

Net: the nav reads as a **per-storefront capability map** — what you see = that node's resolved modules ×
your role permissions × node tier.

---

## 8. The single architectural change that delivers this

Today the pieces exist but are **welded together** — specifically, loyalty earn is fused into the order
flow (`_compute_earn()` keys off the order amount; Engagement only knows "a sale happened" by being
*inside* `orders`). The decoupling work:

**Introduce a `loyalty event` abstraction** that Engagement earns off, accepting three input kinds:

1. **sale event** — from Table QR / POS via `record_sale()` → verified spend → spend-based earn (today's path);
2. **check-in / visit** — stamp earn, no sale (the counter-QR mechanic);
3. **manual / receipt** — merchant-asserted (behind anti-fraud guardrails — caps, OCR confidence, pending-review; **never wired to the coalition pool**).

Move earn behind this event seam and add #2/#3, and Engagement becomes a true standalone module — which
is the entire point of the counter-QR launch. Everything else is wiring around it.

## 9. Mapping to current build (verified 2026-06-07)

The moat machinery is largely built; it is built **fused**, not toggleable. The work is a refactor + two
small builds, not a rebuild.

| Piece | Today | Gap to make it an independent module |
|---|---|---|
| **Table QR** | ✅ full capture loop (`api/routes/qr.py`, `orders.py`, `catalog.py`) | **KDS / order-display screen** so it can fulfil when POS is off (backend order feed `list_orders` exists; no dedicated UI) |
| **POS** | ✅ built (`/pos`, PIN auth, pay, receipt, void — `services/pos_staff.py`, `orders.void_order`) | already fairly standalone; gate behind a POS module flag |
| **Customer Engagement** | ✅ loyalty/coalition/vouchers/CRM/RFM/win-back/campaigns/AI all built (`loyalty/engine.py`, `models/loyalty.py::Coalition`, `analytics/rfm.py`, `crm.py`, `vouchers.py`) — **but earn is welded to a sale** | **break the weld** (§8): the `loyalty event` abstraction + **counter-QR join flow** + **check-in/stamp earn** + **member identity QR** |
| **Shared Customer Directory** | ✅ implicit (customers + orders) | formalise as the always-on raw slice beneath Engagement |
| **Module flags** | 🟡 partial (`qr_ordering_enabled`, `rewards_enabled`; `test_module_gating.py`, `test_module_flags_boundaries.py`) — flat on `Merchant.settings`, not tree-cascaded | **rationalise into 3 tree-cascaded module flags on `org_nodes`** (+ add POS), resolve per §7, enforce the §5 degradation rules, drive adaptive nav |
| **record_sale() hub** | 🟡 the 3 channels (QR/POS/manual) exist but don't yet funnel through one core (Foundation #6, [[ingestion-seam]]) | make it the single seam that records the txn **and emits the sale event** |

### Known gaps surfaced (not yet built)

- Counter-QR **join-only** sign-up flow (enroll without ordering) — the LAND front door.
- **Check-in / stamp** (visit-based) earn mechanic — earn is spend-based only today.
- **Member identity QR** in the customer app (for staff-scan / manual redeem).
- **Referral loop** (invite-a-friend, both earn) — the customer-side multiplier (lives in Engagement).
- **KDS / order-display** merchant screen.

## 10. Build / refactor sequence (suite-green each step)

1. **`record_sale()` as the event hub** — funnel QR/POS/manual through one core that records the
   `Transaction` and emits a sale event. (Foundation #6; no behaviour change, pure convergence.)
2. **`loyalty event` abstraction** — Engagement earns off the event, not the order. Existing spend-based
   earn becomes "input kind #1." Suite stays green.
3. **Three tree-cascaded module flags + adaptive nav + graceful degradation** — move flags onto
   `org_nodes` with the §7 cascade/natural-scope resolution; drive the side menu off the resolved set
   (§7.3–7.5); enforce §5 clean disabled-responses; hide nav for off modules.
4. **Counter-QR join flow + check-in/stamp earn + member QR** — Engagement now runs standalone (the LAND).
5. **KDS / order-display screen** — Table QR fulfils with POS off.
6. *(later)* **Referral loop**; the keep-your-POS connectors (inbound API ingest / receipt / outbound
   order-injection) as additive producers on the same seam — see [[ingestion-seam]],
   [[gtm-pos-agnostic-capture]].

## 11. Consequences

- **Positive:** clean SKUs + land-and-expand pricing; the counter-QR launch becomes first-class; future
  keep-your-POS connectors are additive *producers* on the seam (no new plumbing); CRM/marketing never
  leaks into the order flow; matches Foundation #6/#7.
- **Cost:** a refactor (the weld break + flag rationalisation) before new revenue features; discipline
  required to keep modules talking only through the seam.
- **Risk:** if the seam is bypassed (a module reaching into another's tables), independence rots — enforce
  the producer/consumer rule in review. The earn-weld break is the highest-risk step (touches the hot
  accrual path `loyalty/engine.py`); do it behind the abstraction with the ledger reconciliation tests as
  the guardrail.

---

**Related:** [[ingestion-seam]] (Foundation #6 sale core) · [[gtm-pos-agnostic-capture]] (keep-your-POS
producers) · [[voucher-redemption-design]] (rules published by Engagement) · [[member-tree-chain-storefront]]
(the spine in the core) · [[roadmap-mvp-foundation]] (Foundation Contract #6/#7).
