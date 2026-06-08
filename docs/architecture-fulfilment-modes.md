# Architecture — Fulfilment Modes (Ordering module)

_Decision 2026-06-08. CIP's **Ordering** module must serve **every F&B format** by configuration, not by
hardcoding one. A foodcourt does **pickup** (collect-when-ready, order number, no table); a restaurant/café
does **dine-in** (table QR + table number); some do **takeaway** / **delivery**. Fulfilment is a
**per-storefront mode**, table numbering is **conditional on the mode** — never baked in. Status: PLAN
(dine-in built; pickup is the incremental add). Aligns with the Foundation Contract (#5/#6/#7) and the
3-module ADR (`docs/architecture-3-modules.md`)._

## The modes
| Mode | Entry / context | Identifier on the order | Hand-off | Status today |
|---|---|---|---|---|
| **dine_in** | **table QR** | **table number** (`DiningTable`) | deliver-to-table *or* collect | **built** (table-QR flow) |
| **pickup** | stall/court QR or app | **pickup/order number** | collect-when-ready (notify) | to build |
| **takeaway** | stall/court QR or app | order number | bag at counter | to build (≈ pickup) |
| **delivery** | app | order + address | dispatch | deferred (P1 roadmap) |

A storefront declares **one or more** supported modes (a café may offer dine_in *and* takeaway).

## What varies per mode vs what's shared
- **Varies (thin, at the edges):** how context is entered, **which identifier attaches** (table vs pickup
  number vs address), the **hand-off step** + the order **status states** + the customer notification copy.
- **Shared (the whole middle — one pipeline):** stall/menu resolution → cart → checkout → **payment →
  `record_sale()` → loyalty/CRM**. The mode is a variation at entry + hand-off, **not a fork in the core.**

## Data model (additive)
- **Per-storefront config:** `fulfilment_modes` (the supported set) + a default — carried like the module
  flags (org-node config / `Merchant.settings`), resolvable via the cascade. Default by storefront kind.
- **`Order.fulfilment_type`** enum: `dine_in | pickup | takeaway | delivery`. **Default `dine_in`** so
  existing data + the current table-QR flow are unchanged (back-compat). Migration adds the column.
- **Conditional identifier:**
  - `dine_in` → `table_id` (existing `DiningTable` + table QR).
  - `pickup`/`takeaway` → **`pickup_number`** — a short human token (per stall, per day, rotating) generated
    at checkout; shown to the diner, included in the "ready" push, quoted at collection. **No table.**
- **Status lifecycle additions:** a **`ready`** state + a stall **"mark ready"** action (pickup/takeaway);
  `served` for dine_in. The "ready" customer notification reuses the messaging channel.

## Foundation Contract alignment (why this is additive, not a rebuild)
- **#5** — the resolver keys off **seller (stall/menu, `menu.id==node.id`), not table**; `table` is an
  *optional attachment* present only in `dine_in`. Dropping it for pickup breaks nothing.
- **#6** — all modes funnel through **one `record_sale()` core**; the mode is metadata on the sale.
- **#7** — fulfilment is a **capability flag** per storefront.

## Mapping to current code
- **Built:** `DiningTable` + per-table QR (dine_in), foodcourt multi-stall browse
  (`catalog.list_outlet_stalls`), menus, cart, checkout, order status lifecycle, loyalty-on-checkout.
- **To add (the pickup mode):** `fulfilment_modes` storefront config · `Order.fulfilment_type` (+migration,
  default dine_in) · `pickup_number` generation · `ready` status + "mark ready" stall action · ready-notify
  (needs the real messaging channel) · make the table attachment **conditional**.
- **Order-receipt / KDS screen** per stall (receive app orders → mark ready) — pulls a lite slice of the
  P5 KDS forward; the per-stall device in pickup mode is an **order screen, not a loyalty till**.

## Module relationship + naming
This is a **sub-config of the Ordering module**. The current **"Table QR"** label is dine-in-centric; the
module is really **"Ordering · with fulfilment modes."** Keep the familiar label for now, but the engine
underneath is mode-aware. (See `docs/architecture-3-modules.md`.)

## Net
Don't choose foodcourt-vs-restaurant — **make fulfilment a per-storefront mode**, table numbering
conditional. Foodcourt = `pickup`; restaurant = `dine_in`; same platform, a config switch. Building pickup
*as a mode* (not a hack) makes CIP multi-format and reusable for every future client.
