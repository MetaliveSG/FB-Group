# Reference Architecture — Org Tree, Stall Resolution & Loyalty Boundaries

> Status: **design agreed, staged build** (captured 2026-05-30).
> Canonical record of *how the organisation hierarchy is modelled* so the platform scales
> from one hawker stall → a restaurant → a foodcourt → a multi-brand conglomerate without a
> schema rewrite. Complements `roadmap-network-loyalty.md` (which covers the loyalty/FX
> economics); this doc is the **structural** source of truth. The **build sequence** to get here
lives in `archive/implementation-phases.md` (SUPERSEDED build-sequence record; Phase 0 seams → 1 spine → 2 boundaries → 3 POS API → 4
multi-domain/rollup, with the current-state scorecard and P0 risks).

---

## 1. The core decision: roles on a tree, not fixed levels

The instinct is a fixed chain `Platform → Merchant → Brand → Outlet → Stall`. That is the
**wrong mental model** — it hard-codes a depth, and real orgs are *ragged* (a conglomerate
is deep; a single hawker is shallow; a stall can hang off a foodcourt outlet *or* be a
standalone restaurant with no stall layer at all).

The right model is **one self-referential node tree, where a node's `role` — not its depth —
defines what it is**, and a **stall is simply the leaf role** that may attach at *any* depth.

```
                 (role)
PLATFORM   ──────────────── root
   │
   ├── MERCHANT  ─────────── the business / billing tenant
   │     └── BRAND
   │           └── OUTLET    ── a physical location
   │                 └── STALL  (leaf)   ← may also attach directly higher up
   │
   └── MERCHANT
         └── OUTLET          ── (no brand layer — allowed; ragged)
               └── STALL
```

- **There is no separate "stall layer" to add.** A stall is a leaf node. Today it already
  exists as `Menu` under an outlet (the foodcourt feature). "Do we need a stall layer now?"
  → No. We need leaves, and we have them.
- **A leaf can attach at any depth.** A stall under an outlet, a standalone restaurant whose
  outlet *is* effectively the leaf, a stall promoted directly under a merchant later — all
  the same uniform tree.
- **New levels = new roles, never a schema change.** A future `REGION` or `DIVISION` between
  merchant and outlet is just another role on the same tree.

### One node type + capability flags (not two rigid types)

There are not two account types (chain vs stall). There is **one `Node`** (the chain — unlimited
depth, the member_map), plus **capability flags** that say what a node *does*. The instinct
toward "chain vs stall" is really one flag: **does this node sell?**

| Flag | Meaning |
|---|---|
| `sells` | this node is an **orderable endpoint** (has a menu / takes orders) — a "Storefront". The "stop the chain" terminal. |
| `is_settlement_boundary` | money collected at/under here settles to this node (§5) |
| `is_loyalty_domain` | this node is a free-coin ring root (§5) |

- A node is a **Chain node** (pass-through structure) or a **Storefront** (`sells=true`) — and it
  can even be **both** (a flagship that has sub-counters *and* sells up front). A flag expresses
  that; two rigid types cannot.
- `role` (`PLATFORM` / `ENTERPRISE` / `MERCHANT` / `BRAND` / `OUTLET` / `STALL` …) is kept only
  as a **display label** for humans; the *engine* keys off the flags, not the label. Adding a
  level is a new label, never a schema change.

> **`ENTERPRISE` — optional conglomerate tier (agreed shape; NOT built / not needed now).**
> A customer that owns *several merchants* (e.g. NTUC → Foodfare + Kopitiam + leased stalls;
> BreadTalk → Din Tai Fung + Toast Box + bakery) gets an `ENTERPRISE` node above its merchants.
> Crucially it is **optional and ragged** — a solo hawker / single restaurant attaches straight
> under `PLATFORM` with **no** enterprise parent; do not force a hollow Enterprise level on the
> ~95% single-merchant case. Distinct from `PLATFORM` (the SaaS operator — us): an Enterprise is
> a *customer* group. **Boundaries:** the Enterprise carries the **loyalty domain**
> (`is_loyalty_domain=true` → coins free across all its merchants; crossing to another
> enterprise = a clearing fee) and optionally the billing/contract umbrella — but the
> **settlement boundary stays at the merchant** (each merchant / leased stall files its own GST
> and takes its own payout; the Enterprise does not collect money). Additive when a real
> conglomerate signs: a role label + `is_loyalty_domain` on the enterprise node + point its
> merchants' `loyalty_domain_id` at it. No schema change (the spine already supports it).

```
PLATFORM
  ├── ENTERPRISE "NTUC"            ← loyalty-domain node (only for conglomerates)
  │     ├── MERCHANT Foodfare            (settles its own money)
  │     ├── MERCHANT Kopitiam
  │     └── MERCHANT "Leased Stall X"
  └── MERCHANT "Joe's Hawker Stall"  ← solo merchant: no enterprise parent
```

> **Naming:** *Chain node* (structural) and *Storefront* (`sells`) — both intuitive in F&B and
> scale to stall / restaurant / kiosk / cloud-kitchen. "Stall" is fine only where everything
> orderable really is a stall.

### Modular capabilities — merchants adopt only what they want

The platform is a **suite**, not one monolith: some merchants want **rewards only**, some want
**table-QR + rewards** (no POS), some want the **full stack**. These are more capability flags
on the node, **inherited down the subtree** (a merchant subscribes; storefronts inherit, with
per-node override — same resolution as the boundary flags):

| Module flag | Enables |
|---|---|
| `rewards_enabled` | loyalty / the capture loop — the **base product, stands alone** |
| `qr_ordering_enabled` | table-QR menu + order capture (ticket to staff/kitchen) |
| `pos_enabled` | payment, till, cashier/manager logins, settlement, daily close |

Common bundles (the toggles are independent; rewards is the usual base):

| Bundle | rewards | qr_ordering | pos | Behaviour |
|---|---|---|---|---|
| **Rewards-only** | ✅ | ❌ | ❌ | no menu/till; coins captured via a light path (static "join/earn" QR, staff enters phone+amount, receipt scan, or a push from the merchant's own POS). Platform never touches the order or money. |
| **Table-QR + Rewards** | ✅ | ✅ | ❌ | order at the table → ticket to staff; **payment & fulfilment stay with the merchant**; no platform till, **no settlement boundary** (§5). |
| **Full** | ✅ | ✅ | ✅ | + payment, till, POS roles (§4), settlement (§5), daily close. |

These flags **gate the rest of this doc**: the QR resolver (§4) branches on them (ordering on →
menu; off but rewards on → an "earn / check rewards" screen); POS roles (§4) and the settlement
boundary (§5) exist only when `pos_enabled`; and the enabled module set *is* the pricing tier,
so platform-fee config (§6) follows naturally. **Rewards is the core (the capture loop); QR and
POS are layers — "rewards only" is the foundational tier, not a degraded one.**

---

## 2. Structure vs. attributes — a thin spine + typed profiles

Keep two things separate (this is the pattern that lets a uniform tree coexist with rich,
type-specific columns):

- **Spine** — one thin table holding *only structure*: identity + parent + role + depth + path.
- **Profiles** — the existing typed tables (`Merchant`, `Brand`, `Outlet`, `Menu`) hold the
  *attributes* (address, timezone, cuisine, logo, settlement settings…), keyed 1:1 to a spine
  node. We do **not** throw these away or collapse everything into a JSON blob.

> **Δ as-built (2026-06-07):** the shipped `org_nodes` table adds `name`, **`chain_stopped`**, and
> **`subscription_fee`** Numeric(12,2) (migrations `q4r5orgnodename`/`r5s6chainfee`), and does **NOT** yet
> carry the three module flags in the DDL below — `rewards_enabled`/`qr_ordering_enabled`/`pos_enabled`
> live flat on `Merchant.settings` today (`services/boundaries.py::MODULE_FLAGS`). Moving them onto the
> spine with the subtree cascade is the plan in `architecture-3-modules.md §7`. The `path`/`sells`/boundary
> flags + boundary pointers below are as-built.

```sql
-- The spine. One row per org node, any role, any depth.
CREATE TABLE org_node (
    id          VARCHAR(32)  PRIMARY KEY,          -- stable hex UUID (never encodes position)
    parent_id   VARCHAR(32)  NULL REFERENCES org_node(id),
    role        VARCHAR(16)  NOT NULL,             -- DISPLAY LABEL only: PLATFORM|MERCHANT|BRAND|OUTLET|STALL…
    depth       SMALLINT     NOT NULL,             -- cached level (root = 0); avoids recomputing
    path        VARCHAR(512) NOT NULL,             -- materialised path, e.g. 'a1.b2.c3'  ← see §3
    -- capability flags — the engine keys off these, not `role` (see §1):
    sells       BOOLEAN      NOT NULL DEFAULT false, -- orderable endpoint (a "Storefront")
    is_settlement_boundary BOOLEAN NOT NULL DEFAULT false,
    is_loyalty_domain      BOOLEAN NOT NULL DEFAULT false,
    -- module adoption — inherited down the subtree, per-node override (see §1):
    rewards_enabled      BOOLEAN NULL,              -- loyalty / capture (base product)
    qr_ordering_enabled  BOOLEAN NULL,              -- table-QR menu + order capture
    pos_enabled          BOOLEAN NULL,              -- payment, till, POS roles, settlement
    -- resolved boundary pointers (nearest ancestor that declares each; see §5):
    loyalty_domain_id    VARCHAR(32) NOT NULL,     -- the free-coin ring this node belongs to
    settlement_account_id VARCHAR(32) NOT NULL,    -- who collects the money for this node
    is_active   BOOLEAN      NOT NULL DEFAULT true
);
CREATE INDEX ix_org_node_parent  ON org_node(parent_id);
CREATE INDEX ix_org_node_path     ON org_node(path);          -- powers the prefix query in §3
CREATE INDEX ix_org_node_sells    ON org_node(path) WHERE sells;  -- fast "sellable nodes under X"
CREATE INDEX ix_org_node_domain   ON org_node(loyalty_domain_id);
```

The typed tables become profiles: `outlet.id == org_node.id` for the node whose `role='OUTLET'`.
Traversal/scoping reads the spine; attribute reads hit the profile.

---

## 3. Adjacency is clean but slow when lines go deep — add a materialised path

A pure **parent-pointer (adjacency list)** is the simplest correct tree: `parent_id` and
nothing else. It is perfect for writes and shallow reads. **But "everything under node X"
requires walking the chain** — a recursive CTE that gets progressively slower the deeper the
line goes. For a deep conglomerate that is a real cost on the hottest read (the QR
subtree query).

**Fix: carry a materialised `path` column alongside `parent_id`** — a dotted lineage of node
keys from the root:

```
node A1 (root)        path = 'a1'
  └ B2                path = 'a1.b2'
      └ C3            path = 'a1.b2.c3'
          └ D4 (leaf) path = 'a1.b2.c3.d4'
```

Then "the whole subtree under `a1.b2`" is a single **index range scan**, no recursion:

```sql
SELECT * FROM org_node
WHERE path LIKE 'a1.b2.%'          -- all descendants of a1.b2, at any depth
  AND role = 'STALL'               -- e.g. just the orderable leaves
  AND is_active = true;
```

- **`parent_id` stays the source of truth** for the structure (the one thing that must be
  correct); `path` and `depth` are **derived caches** maintained on insert/move.
- **Subtree read = O(matching rows)** via the `path` index, independent of depth — instead of
  O(depth) recursive hops per node.
- **Moves/re-parents** rewrite `path`/`depth` for the moved subtree only (`UPDATE … WHERE path
  LIKE 'old.%'`). Re-parents are rare; reads are constant — the right trade for an org tree.
- Use short stable keys in the path (a per-node base36 code or the id prefix), not the full
  display name, so the column stays compact and immutable under renames.

> Rule of thumb: **adjacency for truth + writes, materialised path for fast subtree reads.**
> Keep both in sync; never derive structure from `path` (it is the cache, not the source).

---

## 4. Resolution by context — one tree, three read-paths

A node is structural or **sells** (see §1: one node type + a `sells` capability flag — not two
rigid types). The same tree is read three ways; the difference is **where you anchor and how
far the radius reaches.**

```
resolve(node, context):
   if node.sells:   show this node's own menu          (a stall, or a standalone restaurant)
   else:            show the sellable nodes in scope    (a directory)
```

| Context | Who | Anchor | Radius | Ordering |
|---|---|---|---|---|
| **QR scan** | customer, physical | the **venue node** the QR is bound to | **this location only** — its own sellable stalls; never the wider chain | dine-in (local) |
| **Mobile app** | customer, digital | the **user** (domain / favourites) | the **full subtree** — all sellable nodes via `path LIKE 'domain.%' AND sells` | pickup / delivery / scheduled |
| **POS / staff** | manager, cashier | the **node the role is assigned to** | acts **down its subtree** (manage all sellable nodes beneath) | operate (take orders, payments, close) |

**QR is location-scoped.** A QR is bound to a physical table at a venue. It shows what is
orderable *there and now* — the venue's own stalls — and stops at the location:

| QR at… | Result |
|---|---|
| a **foodcourt/coffeeshop** (shared table) | that venue's stalls (its direct sellable children) — *not* other venues |
| a **single stall / standalone restaurant** (`sells`) | that **one** menu |

It never walks siblings or the wider network (you can't eat dine-in from a stall 10 km away).
The frontend picks inline-menu vs directory purely on the returned count.

**The app is network-scoped** — deliberately traverses the whole subtree for discovery. This
is *why* the materialised `path` matters more here than for QR: the app is the deep
`path`-prefix read; QR is a cheap "sellable children of this venue" lookup. Keep **dine-in
physically gated** (must scan / be present); **pickup/delivery is open** across the chain —
otherwise someone "orders dine-in" at a stall they are not sitting in.

**POS / staff is operator-scoped** — a role is scoped to a `node_id` and its authority
**cascades down the subtree** (the same `path`-prefix, but for write/manage actions):

| Login | Scope | Can do |
|---|---|---|
| **Cashier @ a Storefront** | that stall node | take orders, accept payment, print receipt |
| **Manager @ a Storefront** | that stall node | + voids, refunds, discounts, price/menu edits, daily Z-report |
| **Manager @ a Chain node** (outlet / brand / merchant) | every sellable node beneath (`path LIKE 'ntuc.kopitiam.%'`) | oversee/manage all child storefronts — regional/operator login |

This is the existing RBAC (`UserRoleAssignment.scope_type/scope_id`, roles
`OUTLET_MANAGER`/`STAFF`) generalised: **scope becomes a `node_id`; permission flows down the
subtree.** Two POS notes: (1) a till **binds to the same node as settlement** — cashier logs
into the *operator* node in aircon (central till) or the *stall* node in non-aircon (own till),
so login scope and money scope (§5) are the same marker; (2) integration is per-node whether
the platform *is* the POS (orders placed in-system) or *feeds an external POS* (order
injection, menu/price sync, payment reconciliation) — orders, receipts and the daily close all
scope to the storefront node and roll up via §6.

So "can any layer straight open the stall layer?" → **yes, natively**: a node resolves to *its
own menu if it sells, else the sellable nodes in scope*, and the scope is set by context.

---

## 5. Two boundaries on the tree — loyalty domain ≠ settlement account

Money and loyalty do **not** live at the same level. Two independent markers, both columns on
`org_node` (see §2), resolved by walking to the nearest ancestor that declares each:

- **`loyalty_domain_id`** — the **free-coin ring**. Coins are at par (no fee) anywhere inside
  the same domain; crossing domains triggers a clearing **fee** (see economics in the roadmap
  doc). A coin is **stamped with its `loyalty_domain_id` at the moment it is earned**, in an
  **append-only ledger** — this is the one value that cannot be reconstructed later and must be
  recorded from coin #1.
- **`settlement_account_id`** — **who collects the money**. This is *variable per venue*, which
  the foodcourt formats prove:

| Venue format | Who collects | `settlement_account_id` resolves to |
|---|---|---|
| Operator-run court (e.g. aircon, central cashier) | the operator | the **operator** node (one account) |
| Vendor-run court (e.g. non-aircon, pay each stall) | each stall | the **stall** node (per-stall) |

A per-outlet setting (`settlement_mode = operator | per_stall`) chooses which ancestor a sale
settles to. The **same brand/format can be either** — so settlement can never be welded to a
fixed level; it is a resolved marker.

Because these are two separate columns, a stall can settle its own money (`settlement_account
= stall`) while still sitting inside a group-wide free-coin ring (`loyalty_domain = the group`)
— the case where independent vendors share one loyalty programme.

When the optional **`ENTERPRISE`** tier exists (§1), it is the natural **loyalty-domain** node:
coins are free across all the enterprise's merchants, and crossing to another enterprise is the
clearing fee. The **settlement boundary still stays at the merchant** (each merchant / leased
stall collects + files its own money) — so loyalty domain (enterprise) and settlement (merchant)
sit at different levels, which is exactly what these two independent markers allow.

---

## 6. Value rollup engine — money & coins flowing through the tree

The org tree says *who is above whom*; the rollup engine says *what each node earns when
something happens below it*. A value event always originates at a **leaf** (a sale, a coin
earn at a stall). The engine reads the leaf's **`path`** (which *is* the ordered ancestor
list — no recursion), walks the line, applies **each edge's terms**, and posts a balanced
entry per beneficiary into the **append-only ledger**. So the materialised `path` does double
duty: fast subtree reads *down* (§3) and a ready-made ancestor list for rollup *up*.

### The primitive: a per-node rate on the member_map — direction is just config

The fundamental unit is **one rate set on a node in the map**. "Platform fee vs royalty" and
"inflate down vs accumulate up" are **not structural** — they are just *configurations* of
per-node rates. The schema does not encode direction or fee-type; it stores, per node, a rate
+ what base it applies to + who the beneficiary is, and **the engine is one generic loop:**

> For each node on the leaf's `path`, apply that node's rate to its base and credit its
> beneficiary.

That single mechanism produces every variant — set differently per layer in the map:

```sql
CREATE TABLE org_node_terms (
    node_id     VARCHAR(32) NOT NULL,   -- the node this rate is set on (the "member_map" entry)
    kind        VARCHAR(16) NOT NULL,   -- free label: platform_fee | royalty | override | rebate | coin_split …
    calc        VARCHAR(12) NOT NULL,   -- PERCENT | FIXED | PER_UNIT  ← fixed amount OR percentage
    rate_bps    INT NULL,               -- used when calc=PERCENT (e.g. 100 = 1%)
    amount      NUMERIC(12,2) NULL,     -- used when calc=FIXED (per event) or PER_UNIT (× qty)
    min_amount  NUMERIC(12,2) NULL,     -- optional floor/cap on a PERCENT term
    max_amount  NUMERIC(12,2) NULL,
    base        VARCHAR(16) NOT NULL,   -- GROSS (leaf sale) | PASSTHRU (amount handed up/down) | …
    beneficiary VARCHAR(16) NOT NULL,   -- SELF | ROOT | <ancestor node_id>
    valid_from  TIMESTAMP NOT NULL,
    valid_to    TIMESTAMP NULL
);
```

Effective-dated so a rate change writes a new row and last period's close still computes
against last period's terms.

**Fixed amount *or* percentage** — `calc` decides: `PERCENT` (e.g. 1% of base), `FIXED` (a flat
amount per event, e.g. $0.20/order), or `PER_UNIT` (flat × quantity, e.g. $0.10/item). A
`PERCENT` term may also carry `min_amount` / `max_amount` (e.g. 1% but floor $0.10, cap $5). The
engine loop is unchanged — it just reads `calc` to compute the slice. One caveat: a *recurring*
flat fee (e.g. a $500/month franchise fee) is **not** a per-event term — it is a separate
scheduled posting, since this engine fires only on leaf events (sales / coin earns).

### Platform fee and royalty are the same primitive, configured differently

Because every layer's rate is set on its own node in the map, "platform fee" and "royalty" are
**just two configurations of the per-node rate — the up/down direction does not matter to the
schema or the engine.** They differ only in their `base` and `beneficiary` config:

| Config | `base` | `beneficiary` | *Reads as* | We earn it? |
|---|---|---|---|---|
| Platform fee | `PASSTHRU` (the fee handed down) | `ROOT` | a fee "inflating down" — each level keeps its markup spread | **Yes** |
| Royalty / override | `GROSS` (the leaf sale) | `SELF` (the ancestor) | a cut "accumulating up" | No — settled for the merchant |

Same loop, different rows. Worked the two ways:

```
Platform-fee config (beneficiary=ROOT, base=PASSTHRU)   Royalty config (beneficiary=SELF, base=GROSS)
  NTUC      1.0%  → keeps 0.5% spread                     Kopitiam 5% of $10 → $0.50
    Kopitiam 1.5% → keeps 0.5% spread                       NTUC override 2% → $0.20
      stall PAYS 2.0%  (1% "inflated" to 2%)                  stall keeps $9.30
```

The "inflate-down" and "accumulate-up" pictures are just how you *read* the same per-node
rates — one resolves the leaf's effective rate by walking down, the other distributes the
leaf event by walking up. The engine doesn't care which: it applies each node's own
configured term. **Any layer can be set independently in the member_map**, which is the whole
point — you never hard-code direction or fee-type into the structure.

### Coins roll up the same way

The same ancestor walk handles loyalty, just to different ledger accounts:

- A stall mints coins → the **coin liability** posts at the **`loyalty_domain`** node that
  underwrites them (not the stall).
- **Breakage** (coins expiring unredeemed) rolls up as recognised revenue at the domain /
  platform.
- A **cross-domain redemption** posts the clearing **fee / FX spread** on the edge that
  crosses the loyalty-domain boundary — the only place "cross-merchant has fees" fires. A
  royalty, by contrast, is intra-business money on a sale and involves no coin crossing.

### Direction flips with settlement mode

- **Vendor-run (e.g. non-aircon):** the stall collects, then pays royalty/rent *up* — royalty
  flows up as above.
- **Operator-run (e.g. aircon):** the operator already holds the money and *pays the stall*
  its share — value flows *down* as an internal payout; there is no "royalty up." The same 5%
  is "royalty the stall owes" in one mode and "operator payout to the stall" in the other —
  the `settlement_account_id` marker (§5) decides which.

### Caps & compression

Because markup-down and cut-up each compound per level, deep trees can over-inflate (leaf fee
too high) or over-skim (stall keeps too little). So bound both:

- a **max effective platform fee** at the leaf (cap the prefix sum),
- a **max cumulative royalty**, and
- **compression** — skip inactive ancestors, or cap rollup at N levels (e.g. platform fee only
  at the root, royalty only at the brand).

These are rules in the walk, configured per term — not schema.

### Live estimate vs. authoritative close

The live view is an **estimate** (show a stall "today's takings" instantly). The authoritative
split is a **periodic close** that runs over a *frozen snapshot* of the tree + terms, posts the
final immutable entries, and reconciles the estimate. This is why the ledger is **append-only
and effective-dated**: the close must be reproducible and auditable. With `path`, the close is
a set-based join over ancestors, not a per-event recursive walk — which is what keeps a
month-end run over millions of events tractable on a deep tree.

> **Status:** deferred — build when value rolls up more than one level (a franchise deal, or
> the cross-domain coin fee going live). Kept additive by the foundational items in §7:
> append-only domain-stamped ledger + the materialised `path`. Given those, the whole engine
> is a pure read-side addition — no rewrite.

---

## 7. What is foundational (do now) vs additive (defer)

**Foundational — get right now, cheap, expensive to retrofit:**

1. **Stable opaque ids** that never encode position (already true — hex UUIDs).
2. **Append-only coin ledger**, idempotent, each entry **stamped with `loyalty_domain_id`**.
   Treat any cached balance as a reconcilable projection of the ledger, never the source.
3. **Code scopes by boundary id** (`loyalty_domain_id` / `settlement_account_id`), never by
   structural traversal or an assumed depth. No `"3 levels"` assumptions in business logic.
4. **Uniform QR resolution semantics** (token → node → subtree-or-self). ~80% already built in
   the foodcourt feature; works on the *current* typed tree before the spine exists.

**Additive — build when a real case pulls it (no rewrite if the above hold):**

- The `org_node` **spine + materialised path** (this doc's §2–§3). Migrate by backfilling one
  spine row per existing entity; point traversal/scoping at the spine; keep typed tables as
  profiles. Pull this forward when org depth exceeds merchant→brand→outlet or stalls must
  attach at varying levels.
- Cross-domain **fee / FX** posting + the clearing ring config.
- A **venue** abstraction for tables/QR shared across *different* merchants (vendor-run courts).
- **Value rollup engine** (platform fee, royalties, coin breakage / clearing) — see §6 for the
  full design (per-node terms on the member_map, the generic one-loop engine, caps, close).

---

## 8. Migration from today (additive, IDs stable)

| Today | Becomes |
|---|---|
| `Merchant` / `Brand` / `Outlet` rows | profile rows; one `org_node` each (`role` label = MERCHANT/BRAND/OUTLET) |
| `Menu` (foodcourt stall) | profile for an `org_node` with `sells=true` (a Storefront) |
| `merchant_id` scoping | `loyalty_domain_id` (loyalty) + `settlement_account_id` (money); both default to the merchant node today |
| QR → outlet → its menus | QR → node → `path`-prefix subtree of `sells` nodes (or self) |
| `UserRoleAssignment` (OUTLET_MANAGER / STAFF) | role scoped to a `node_id`; authority cascades down the subtree (POS/staff) |

No row is destroyed; ids are preserved; the spine is backfilled and kept in sync with the
typed profiles. The current single-merchant / single-domain demo keeps working throughout —
every change is transparent until a second domain or a deeper tree actually exists.

---

## 9. Extensibility / ERP-readiness — the backbone contract

**Goal:** adding competitor-grade features (Qashier / MegaPOS / Reso-class: inventory, KDS,
reservations, e-invoicing, payroll) or expanding into a full **ERP** (procurement, general
ledger, HR, consolidation) must be **additive modules on a stable backbone — never a
re-architecture.**

You cannot pre-build unknown futures, and trying is itself the overhaul you are avoiding (wrong
abstraction lock-in). "No overhaul" comes from getting a **small set of backbone primitives**
right so ~90% of future features slot in as modules.

### The backbone (get these right; features hang off them)

| Primitive | What it is | Have? |
|---|---|---|
| **Org spine** (Node + `path`) | everything is node-scoped; new module data attaches to a node | designing (Phase 1) |
| **Generic posting ledger** | one append-only, idempotent, double-entry posting log — coins, money, **stock moves, GL entries** are all postings | coin ledger ✅ — *generalise the pattern* |
| **Document + lines + workflow** | header + lines + status + postings — order today; **invoice / PO / goods-receipt / stock-transfer / payroll** tomorrow | order ✅ — *treat as first instance* |
| **Catalog as products** | item general enough to be sellable + stockable + recipe/BOM-composable | MenuItem ✅ — keep general |
| **Module flags** | à-la-carte adoption per node (§1) | designing (Phase 0/2) |
| **Integration substrate** | API keys + inbound API + outbound signed events (§Phase 3) | Phase 3 |
| **Extensible attributes** | JSONB custom fields on core entities | `merchant.settings` ✅ seed |
| **Party + role** | customer / staff / **supplier** as parties with roles | customers + users ✅ |

### Why it holds — competitor/ERP feature → additive module

| Feature | Absorbed by | Overhaul? |
|---|---|---|
| Inventory / stock | stock-movement **postings** + **products**, node-scoped, module flag | No |
| Recipes / BOM / food cost | **product** composition + stock postings | No |
| Procurement (PO → GRN → bill) | **documents** + **supplier party** + GL postings | No |
| Accounting / GL / e-invoicing | the **posting ledger *is* the GL**; e-invoice = document + integration | No |
| Payroll / HR / timesheets | **party** + **documents** + postings | No |
| Reservations / queue / tables | node-scoped + a module flag | No |
| KDS / printers / hardware | **outbound signed events** | No |
| Delivery / e-commerce | inbound/outbound **integration** + orders-as-documents | No |
| Multi-currency / consolidation | **FX on postings** + the **domain tree** | No |

### The two cheap moves that make this true (not aspirational)

1. **Design the append-only ledger as a generic posting substrate** (Phase 0 stamps domain +
   idempotency anyway) — the same shape a stock movement or GL entry will use. Frame it as
   *postings*, not *coin transactions*.
2. **Treat `Order` as the first instance of a document + lines + workflow + postings pattern**,
   so invoice / PO / GRN reuse the shape instead of being special-cased. Plus seed **JSONB
   custom-field** extensibility on core entities.

That is the difference between "inventory/GL is a new module" and "inventory/GL is an overhaul."

### The anti-pattern (equally important)

**Do not build any ERP module now.** Over-generalising ahead of demand is the same lock-in from
the other direction. Build the *backbone*; ship each *module* only when a real customer pulls
it. No-overhaul = **stable primitives + additive modules**, never a speculative mega-model.

### POS client / OS — API-first means the OS is not an architectural choice

The POS is just another consumer of the same API (FastAPI + `@fbgroup/api-client`), like the
customer QR app and the merchant console. So the OS is a **client/delivery** decision — fully
reversible, touching none of the backbone.

- **PWA-first** (reuse the Next.js/web stack) on **Android** all-in-one terminals (Sunmi / iMin /
  PAX — the SG F&B norm: built-in thermal printer, scanner, cash-drawer port, card reader, kiosk
  lockdown, cheap). iPad optional/premium later; Windows not needed.
- Wrap the PWA in a thin **Android shell (Capacitor / TWA)** only for what a browser can't do:
  **peripherals + offline.**
- The hard parts are **offline, peripherals, payments** — already anticipated:
  - **Offline-first:** the POS must keep taking orders/payments through a network drop — local
    queue + sync on reconnect, made safe by the **idempotency keys (Phase 0/3)**; the append-only
    posting ledger is the reconciliation target. (Strongest reason idempotency is foundational.)
  - **Payments/PCI:** card data never touches the app — the EMV/NETS pinpad tokenises; the app
    posts a *tokenised* payment. Rails (NETS / PayNow QR / cards) integrate per **settlement node** (§5).
  - **Peripherals/KDS:** driven by the Android shell; KDS is an **outbound signed event** (Phase 3).
- **Build order:** PWA now (any tablet, demo + lite merchants) → Android wrapper + offline +
  peripherals when a merchant needs full POS. Additive — the API is the contract.

### Inventory & suppliers — the first ERP module (deferred; hooks only)

"Extend later if needed" — and it needs **no new foundational work**; it lands entirely on the
backbone above:

- **Supplier** = a **party** (+ role) · **stock** = **stock-movement postings** on the generic
  ledger · **products** = the generalised catalog · **procurement (PO → goods-receipt → bill)** =
  **documents** · gated by an `inventory_enabled` **module flag**.
- Naturally **node-scoped**: each outlet / central kitchen / stall is a node that *holds* stock;
  **transfers between nodes are postings** (central kitchen → outlet → consumed). **Recipes/BOM**
  = product composition; selling a dish depletes ingredient stock via postings; **food cost** =
  valuation on those postings.
- Inventory is the clearest proof of the contract: `org spine + posting ledger + products +
  documents + party + module flag` — **all already in the backbone.** Keep the hooks (don't
  special-case orders or the ledger); build the module when pulled.

---

## 10. Venues & leasing — foodcourt vs coffeeshop (physical ≠ ownership)

> **STATUS (2026-06-02):** **BUILT** — one associative `leases` table (`app/models/leases.py`,
> migration `s6t7venuelease`), **no columns on `org_nodes`**; `rent_type` (FIXED|GTO) on the edge gates
> visibility (`app/services/leasing.py::gto_turnover_grants` → read-only turnover for GTO, nothing for
> FIXED) and the `storefronts_at_venue` shared-QR resolver. **Managed from the Platform Console** — the
> venue node's NodeDetailDrawer has a **Tenancies** section (`GET/POST/PATCH/DELETE /org/nodes/{venue}/leases`)
> where `rent_type` is a FIXED/GTO dropdown. Proven by `app/tests/test_leasing.py` + the BreadTalk seed
> (BT Coffeeshop @ AMK on FIXED, Mr Bean on GTO), live on Docker. **Deferred:** per-sale GTO settlement
> split, rent invoicing (B2B + GST-on-rent), wiring the customer QR route to the resolver.

The tree models **ownership** (whose money, whose loyalty, who manages). But *where a stall
physically sits* is a **different axis** — and Singapore F&B proves it with two look-alike layouts
that are opposites underneath:

| | **Foodcourt (GTO rent)** | **Coffeeshop / kopitiam (fixed rent)** |
|---|---|---|
| Rent | % of the stall's gross turnover | fixed $/month |
| Landlord sees the stall's sales? | **Yes** — needs it to bill the % | **No** — sales are private to the tenant |
| Tenant in landlord's value-rollup? | Yes (read-only turnover) | **None** |
| Shared table / one QR? | Yes | Yes |

Same shared seating, same single table QR — **opposite** on the only axis that matters: *does the
landlord see the sales?* That tell-tale means **physical co-location and ownership/visibility are
independent**, so we model them independently.

### Three orthogonal things (not two)

1. **Ownership / settlement** — the Chain/Storefront tree (`parent_id` + the §5 boundaries). *Who
   gets the money.* A coffeeshop tenant is its **own** branch — NOT under the coffeeshop.
2. **Physical venue** — a `venue_id` on a Storefront (nullable; null = "I am my own venue"). The
   shared-tables / shared-QR grouping. *Where you sit / what you can order at this table.*
3. **Lease** — a landlord↔tenant edge `{tenant, landlord(venue), rent_type: FIXED | GTO, rate}`.
   The `rent_type` is the single switch that decides **visibility *and* settlement**.

### The one rule that makes privacy + GTO both work
> **Money & visibility follow the ownership tree (+ explicit GTO lease grants). Tables & QR follow
> the venue. They only coincide when the venue operator also owns the stalls (a house foodcourt).**

This gives the §4 read-paths a third row: a **GTO** lease grants the landlord a **read-only
turnover** path into the leased stall (for billing) — never menu/staff/control; a **FIXED** lease
grants **nothing** (the coffeeshop owner has no code path to a tenant's sales). The rent-model
choice *is* the privacy setting — operators never touch "permissions."

### Three actor types, two primitives
- **Branded chain** (Mr Coconut, BreadTalk) — runs its own outlets → its **own Chain branch**.
  Anything big enough to stand alone *does*, so it won't lease a foodcourt stall.
- **Independent operator** (solo hawker / SME) — a **single Storefront**: standalone, or leased
  into a foodcourt/coffeeshop (own settlement boundary; GTO or fixed).
- **Venue operator** (Food Republic / kopitiam towkay) — a **Chain flagged `is_venue`** holding
  *house* stalls (its children) and/or *leased* stalls (independent branches with `venue_id` here).

### Runtime
QR → venue → list storefronts at that venue (house `sellable_under` ∪ leased `venue_id==venue`);
1 → inline menu, many → chooser. **Multi-vendor cart:** one checkout across stalls → split into
per-storefront orders → each settles to its own tenant (GTO cut to landlord if leased GTO),
**each tenant sees only its own slice.** Settlement split reuses the §6 value-rollup primitive
(a per-node rate, direction = config) — GTO is just royalty pointing *up* to the landlord.

### Wiring to today's model (the cheap part)
We already have the venue and the stall — they're hiding in the typed tables:
- **`Outlet` IS the venue** — a physical place with tables + QR + multiple menus; the QR already
  resolves `outlet → its menus (stalls)` (`qr.py`). That *is* the shared-QR foodcourt, today.
- **`Menu` IS the Storefront/stall** — the sellable leaf, already 1:1 with a spine node.
- **House foodcourt already works** — Bedok Food Hall / Hawker Hub = one outlet, many menus, one
  owner. No new code.

So the **only** genuinely new work is leasing:
1. **Let a stall belong to a different tenant than the venue's owner.** Today every `Menu` under an
   `Outlet` shares the outlet's `merchant_id`; a leased stall's money goes to a *different* tenant.
   → the stall's Storefront node carries its own settlement boundary, decoupled from the venue.
2. **Add the `Lease` record** (venue ↔ stall, `rent_type`, rate).
3. **The rent-type visibility rule** (GTO → read-only turnover grant; FIXED → nothing) + later the
   **split settlement** (§6 engine). Additive, IDs stable (see §8) — nothing existing breaks.

### Consumer entry — **every node is addressable** (QR = dine-in, app = browse)

The QR and the web/app are the **same resolver pointed at a node**. Every node has a stable public
token (today's QR slugs are exactly this — stable per outlet+table; generalise to one-per-node). You
point the consumer surface at *any* node, and it branches on kind:

| Pointed at | Diner sees |
|---|---|
| a **Storefront** | the menu → order |
| a **venue** (a specific foodcourt/kopitiam/restaurant) | the stalls at *that location* |
| a **brand/group Chain** — "Food Republic (All Locations)", "Toast Box (All Locations)", "BreadTalk Group" | a **location/brand browse** → pick location → stalls → menu |

> **As-built (§12.2):** today the `/t/node/{id}` browse lists a node's **direct** sellable children +
> stalls leased directly into it (the location model) — *not* the whole subtree. The full-subtree
> "group app" browse is a deferred `?mode=` on the same resolver. A storefront in the browse links
> straight to its own `/t/{token}` ordering page.

- A **QR** is just a node-link that **also carries a table + dine-in mode** (so the order is seated
  here, now). An **app deep-link** is the same node-link **without** a table → browse / takeaway /
  delivery / pick-a-location.
- The node you wire an app to also sets its **loyalty ring** (that node's loyalty domain, §5) and
  its **branding scope** — so a white-label *"Food Republic app"* = the Food Republic node, and
  coins work across **all** its locations automatically; a *"BreadTalk Group app"* spans the whole
  group's domain. The member tree *is* the consumer navigation **and** the white-label boundary.

**Wiring to today:** the customer route is already `/t/{token}` resolving a token → dining context
(`qr.py`). Generalise the token to point at **any node** + a **fulfilment mode** (dine-in carries a
table; takeaway/delivery don't). One resolver, one tree — QR, brand app, and group app are all just
"which node, which mode."

---

## 11. Summary

- **One node type + capability flags, not fixed levels / not two account types.** `sells`
  marks an orderable Storefront; `role` is just a display label. Stall = a node that sells.
- **Modular adoption:** `rewards_enabled` / `qr_ordering_enabled` / `pos_enabled` (inherited
  down the subtree). Rewards-only, table-QR + rewards, or full — rewards is the core; QR & POS
  are layers. The enabled set gates the QR resolver, POS/settlement, and the pricing tier.
- **Thin spine (structure) + typed profiles (attributes).**
- **Adjacency (`parent_id`) for truth + writes; materialised `path` (`a1.b2.c3`) for fast
  `LIKE 'a1.b2.%'` subtree reads** — because pure parent-pointer walks degrade on deep lines.
- **One tree, three read-paths by context:** QR = **location-scoped** (this venue's stalls,
  dine-in), app = **network-scoped** (whole subtree, pickup/delivery), POS/staff =
  **operator-scoped** (role on a node, authority cascades down the subtree).
- **POS/RBAC:** Cashier/Manager roles scope to a `node_id`; permission flows down the subtree;
  the till binds to the same node as settlement (operator vs stall).
- **Two boundaries:** `loyalty_domain_id` (free-coin ring) and `settlement_account_id`
  (who collects — variable per venue: operator vs per-stall).
- **Value rollup:** per-node terms on the member_map (fixed *or* %); fee/royalty & up/down are
  just config; one generic engine; caps + periodic close.
- **Foundational now:** stable ids, append-only domain-stamped ledger, scope-by-boundary-id,
  uniform resolution. **Spine + path, fees/FX, venue, rollup:** additive when a real case pulls.
- **ERP-ready by backbone, not by pre-building (§9):** generic posting ledger + document/lines
  pattern + products + module flags + integration + custom fields ⇒ inventory, GL, procurement,
  payroll, KDS, delivery all slot in as **additive modules, no overhaul.** Build the backbone;
  ship modules only when pulled.
- **As-built grounding (§12):** how the shipped code realises the above — storefront provisioning
  (`menu.id == node.id`), the three QR-resolution functions, Tables & QR, and the Enter/console scope.

---

## 12. As-built (2026-06) — provisioning, QR/console resolution, the Enter button

Grounds the **shipped** behaviour against the design (§1–§10). Where the design left a choice open,
this is what the code does today. Two display kinds exist on the spine — **Chain** (`sells=false`,
structural) and **Storefront** (`sells=true`, the leaf) — but the engine keys off `sells`, not the
`role` label (§1). Onboard/manage from the **Platform Console** (`/platform`); rows are
`badge · name · ⋯`, the **⋯ opens the `NodeDetailDrawer`**.

### 12.1 Storefront provisioning — the spine↔typed seam (`app/services/storefronts.py`)
A Storefront created through the console (`POST /org/nodes`, or a `member_kind=storefront` tenant via
onboarding) starts as a spine node only. On create we **auto-provision its typed backing** so it is
immediately scannable + sellable: an `Outlet` (under the tenant's brand) + a **`Menu` with
`id == node.id`** + a `DiningTable` + a stable `QRCode` token (`slug(name)-<nodeid[:8]>`).
- **The invariant the whole resolver stack keys off: `menu.id == node.id`** for a Storefront leaf
  (also how `sync_org_tree` maps a Menu → its Storefront node). The Outlet keeps its own id — it is the
  location/venue and anchors `Order.outlet_id` + the QR token (§2: "outlet = a location, menu = the seller").
- Idempotent (`provision_storefront` no-ops if the Menu exists); `provision_missing(db)` backfills.
- **Do NOT run `sync_org_tree` on operator-built trees** — it would mirror the new Outlet into a second
  (Chain) spine node and re-parent the Storefront. Convergence = the one-tree collapse (deferred).

### 12.2 QR resolution — three functions, three radii (realises §4)
| Surface | Resolver | Radius |
|---|---|---|
| Directory **"QR Menu"** link (`org.py::_qr_paths_for`) | node-keyed | Storefront → `/t/{its OWN outlet token}`; Chain → `/t/node/{id}` *iff* it has direct storefronts |
| **Group browse** `/t/node/{id}` (`qr.py::resolve_node`) | `catalog.direct_storefronts` | **DIRECT** sellable children + stalls leased **directly** into the node — *not* storefronts nested under a sub-chain (matches §4 "QR = the venue's direct sellable children"). Tap a stall → its own `/t/{token}` (`StallRef.order_path`); a foodcourt leased stall with no own token opens an in-place menu sheet. |
| **Venue table scan** `/t/{token}` (`qr.py::resolve_qr` → `catalog.list_outlet_stalls`) | `leasing.storefronts_at_venue` | the venue's house stalls ∪ stalls leased in (the shared-QR foodcourt/coffeeshop set) |
| menu-reachability check `/qr/node/{id}/menu/{mid}` | `catalog.node_scope_stalls` | whole subtree ∪ leased (looser than the display set, on purpose) |

`_qr_paths_for` is **node-keyed**: each Storefront resolves to ITS OWN outlet's token (not the
tenant's first), so a chain of N storefronts yields N distinct QR links. **Deferred:** a full-subtree
"group app" browse (§4 app path / §10 group app) — today `/t/node` is direct-only (the location model);
when built it's a `?mode=` flag on the same resolver, not new plumbing.

### 12.3 Tables & QR (`/merchant/tables`)
Per-storefront table management: add/remove tables, each minted with a unique QR token
(`org_admin.create_table` → `_gen_token`). The QR **image** is rendered client-side (`qrcode.react`,
encoding `{origin}/t/{token}`) with per-table **Print** + **Print-all** printable cards. The add-table
input is a fixed **`T` prefix + a number stepper** (auto-next free number, zero-padded → `T01`, `T02`…).
Locked to the entered storefront's outlet, or an outlet picker in chain/group mode.

### 12.4 The Enter button — scope by the node you enter (realises §4 POS path)
The drill-in context (`OperatorMerchant`: `{ id = tenant merchant, nodeId = entered node,
outletId? = a single storefront }`) decides scope. **Full nav shows in every mode** — entering a node
only *scopes the outlet-keyed surfaces*; it never hides the group tools.

| Enter on… | Context | Menu Editor / Tables & QR | CRM / Orders / Settings |
|---|---|---|---|
| **Storefront** | `outletId` set | locked to its one outlet | tenant-wide |
| **Sub-chain** (e.g. Toast Box) | `nodeId` = the chain | its **subtree** outlets (`menu-admin/outlets?node_id=`) | tenant-wide |
| **Tenant** (settlement boundary) | `nodeId` = tenant | all the merchant's outlets | tenant-wide |

- Any chain is enterable (**"Enter console →"**); a Storefront → **"Enter storefront →"**; **"Open N
  inside →"** drills the directory. `← Back to group` clears the node/outlet scope.
- **Why CRM/Orders stay tenant-wide:** customers + the loyalty ring belong to the tenant
  (§5 `loyalty_domain_id`), not a sub-chain; only outlet-keyed data (menu, tables, sales) sub-scopes.
- **Brands & Outlets are no longer a managed UI surface** — they remain typed FK anchors (§2) only,
  named/created implicitly by provisioning.
