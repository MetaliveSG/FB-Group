# Architecture — Service Options / Fulfilment (Ordering module)

_Decision 2026-06-08, **corrected to the two-axis model 2026-06-10** after studying Toast / Square / Olo.
CIP's **Ordering** module must serve **every F&B format** by configuration, not by hardcoding one — and
crucially **NOT** as a single "dine-in vs pickup" mode (that was wrong). Fulfilment has **two orthogonal
axes**; a storefront configures the **set** of options it offers; the diner/staff **picks one per order**.
Status: PLAN (the "ready" half — KDS + `fulfilment_status` + customer tracker — is BUILT; the config + the
second axis + per-order selection are to build). Aligns with the Foundation Contract (#5/#6/#7) and the
3-module ADR (`docs/architecture-3-modules.md`)._

## How the industry models it (study)
- **Toast — "Dining Options"** (configurable per restaurant; pre-populated Dine In · Take Out · Delivery ·
  Curbside, custom allowed). Each option has a **behavior**: *Dine In* adds **table + server** and the kitchen
  **plates**; *Take Out* requires customer info and the kitchen **packages**; behavior also drives **kitchen
  routing** (different prep stations per option).
- **Square — Orders API** supports **PICKUP / DELIVERY / SHIPMENT only**; **dine-in is POS-app-only** (a
  "dining option", not an API fulfilment type). So Square splits *online fulfillment* from *in-store dining*.
- **Olo — "Handoff Modes"** (pickup · curbside · dine-in · delivery · drive-thru). Dine-in can carry a **table
  number** (brought out); QR → ordering → guest **picks the handoff**; **menu items restrictable per mode**.

**Takeaway:** the pattern is a **configured SET of options, each with behaviors, picked per order**. BUT
Toast/Olo are **restaurant-centric — they bundle "dine-in" = table service**, so they cannot cleanly model
the **SEA foodcourt "eat-in but self-collect"**. CIP wins by **decoupling the two axes** (this is the M4 SEA
operating-model moat, not a Toast clone).

## The two orthogonal axes
| Axis | Values | Drives |
|---|---|---|
| **Dining context** | `eat_in` \| `takeaway` | plate vs **package**; whether a **table** applies; (eat-in may use a shared/own table) |
| **Hand-off** | `self_pickup` \| `served` (\| `delivery` later) | **self_pickup** → order/pickup number + the diner's **"ready for pick-up" notification**; **served** → needs a **table**, a runner/waiter brings it, **NO diner notification** |

**KEY RULE:** the diner **"ready for pick-up" alert keys off the `self_pickup` hand-off — NOT "dine-in"**
(the bug in the old single-axis framing). Dining context and hand-off are independent.

## The 2×2 generates every scenario
| Scenario | dining context | hand-off | Table? | Diner "ready" alert? |
|---|---|---|---|---|
| Foodcourt, eat-in, self-collect | eat_in | self_pickup | no / shared | **yes** |
| Foodcourt, takeaway, self-collect | takeaway | self_pickup | no | **yes** |
| Restaurant, dine-in, waiter serves | eat_in | served | yes | no |
| Restaurant, takeaway | takeaway | self_pickup | no | yes |
| Foodcourt with runners | eat_in | served | yes | no |
| (later) delivery | takeaway | delivery | no | dispatch/track |

## What varies per option vs what's shared
- **Varies (thin, at the edges):** which **identifier** attaches (table vs pickup number vs address), the
  **hand-off** step, the kitchen **plate-vs-package** + **routing**, and the **customer notification** (alert
  only for `self_pickup`).
- **Shared (the whole middle — one pipeline):** stall/menu resolution → cart → checkout → **payment →
  `record_sale()` → loyalty/CRM**. The option is a variation at **entry + hand-off, not a fork in the core.**

## Data model (additive)
- **Per-storefront config:** the **enabled set of service options** + a default — carried like the module
  flags (org-node config, **cascade-resolved** so a foodcourt sets it once high and stalls inherit;
  `Merchant.settings` fallback). Each option = a `(dining_context, hand_off)` pair (named for the UI, e.g.
  "Dine in — self-collect", "Takeaway", "Dine in — served").
- **On the `Order`:** record **both axes** (e.g. `dining_context` + `hand_off`) — or one `service_option` FK
  referencing the chosen option. Today the model has only `order_type` (`dine_in | takeaway | manual`); the
  **`hand_off` axis is the missing piece**. `order_type !== "dine_in"` is the current stand-in for
  `self_pickup` and should be replaced by the explicit hand-off axis. Default = back-compat (`eat_in` +
  `served`) so existing table-QR data is unchanged. Migration adds the column(s).
- **Conditional identifier:**
  - `served` (or any `eat_in`) → `table_id` (existing `DiningTable` + table QR).
  - `self_pickup` → **`pickup_number`** — a short human token (per stall, per day, rotating) generated at
    checkout; shown to the diner, included in the "ready" alert, quoted at collection. **No table.**
- **Status lifecycle (BUILT this round):** the kitchen owns **`fulfilment_status`**
  (`queued→preparing→ready→collected`), separate from payment `status` — see the KDS section in `CLAUDE.md`.
  The diner "ready" alert fires on `ready` **only for `self_pickup`**.

## Foundation Contract alignment (why this is additive, not a rebuild)
- **#5** — the resolver keys off **seller (stall/menu, `menu.id==node.id`), not table**; `table` is an
  *optional attachment* present only when a table applies. Dropping it for `self_pickup` breaks nothing.
- **#6** — all options funnel through **one `record_sale()` core**; the option is metadata on the sale.
- **#7** — service options are a **capability config** per storefront (cascade like the module flags).

## Mapping to current code
- **Built:** `DiningTable` + per-table QR, foodcourt multi-stall browse (`catalog.list_outlet_stalls`), menus,
  cart, checkout, order status lifecycle, loyalty-on-checkout. **NEW (2026-06-10):** the KDS "mark ready"
  screen (`/kds`) + `fulfilment_status` + the customer pick-up tracker — all key off the order's hand-off
  (currently `order_type !== "dine_in"`), so they light up automatically once service options drive it.
- **To add:** the per-storefront **enabled-options config** (cascade-resolved) · the **`hand_off` axis** on the
  `Order` (+migration; the second axis) · **per-order selection** in the QR app (today `t/[token]` hardcodes
  `dine_in`) · the **console control** (NodeDetailDrawer) · **`pickup_number`** generation · **conditional
  table** (only when a table applies) · the **ready notification** via the real messaging channel · (later)
  **per-item availability by option** (Olo-style restrictions).

## Module relationship + naming
A **sub-config of the Ordering module**. The current **"Table QR"** label is dine-in-centric; the module is
really **"Ordering · with service options."** Keep the label for now; the engine underneath is option-aware.

## Net
Don't choose foodcourt-vs-restaurant, and don't model it as one mode — **decouple the two axes** (dining
context × hand-off), let each **storefront configure its enabled set** (cascading), and **pick one per order**.
Same platform, a config switch — and the decoupling natively fits the SEA foodcourt reality Toast/Olo can't.
