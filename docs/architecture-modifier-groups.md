# Architecture — Menu Preferences (Modifier Groups)

_Spec, 2026-06-11 (PROPOSAL — not built). Pitch-driver: **FSG / Fei Siong Group's Malaysia Boleh!**
foodcourt (Jurong Point, 32 Malaysian stalls). Adds **preference groups** to the menu — "Dry/Soup",
"Chilli / No Chilli", "Kopi: O / Peng / sugar" — distinct from priced add-ons. Builds on the existing
`MenuModifier`. Key requirement: **some preferences are REUSABLE across stalls** (a foodcourt operator
curates a shared library) — see §3._

## 1. The need (study: Malaysia Boleh!)
At a real SG foodcourt the diner is asked **preference questions** that aren't add-ons. Four patterns:

| Pattern | Example | Rule | Price |
|---|---|---|---|
| **Dry vs Soup** | Pan Mee · Bak Chor Mee · Yong Tau Foo · Prawn Noodles | pick exactly 1 — **required** | free |
| **Chilli level** | Chilli · No Chilli ("mai hiam") · Less Chilli | pick exactly 1 | free |
| **Drink variants** | Kopi/Teh · O (no milk) · Peng (iced) · sugar level | pick 1 per axis | free |
| **Add-ons** | extra egg · extra meat · more noodles | pick 0..N | **+price** |

**Today's gap:** `MenuModifier` (= `item_id, name, price_delta`) is a **flat, multi-select, priced** list
rendered as toggle chips. It handles add-ons but **cannot express a single-select REQUIRED free choice**
(Dry/Soup, Chilli). `CustomiseSheet` already notes *"no group_name/group_type yet"*.

## 2. The model — modifier GROUPS (Toast/Square "option group" pattern)
A thin grouping layer; the option row stays close to today's `MenuModifier`.

- **`MenuModifierGroup`** — `id`, `owner` (see §3), `name` ("Spice level"), `min_select`, `max_select`,
  `sort_order`, `is_active`.
  - `min_select ≥ 1` ⇒ **required**;  `max_select = 1` ⇒ **single-select (radio)**;  `max_select > 1` ⇒
    **multi-select (chips)**.
- **`MenuModifierOption`** (rename/extend `MenuModifier`) — `group_id`, `name`, `price_delta`
  (default 0), `is_default`, `sort_order`.
- **`MenuItemModifierGroup`** (join) — `item_id ↔ group_id` (+ `sort_order`, optional per-item
  `required` override). **This join is what makes a group reusable** — attach one group to many items.

Every pattern in §1 falls out: Dry/Soup & Chilli = `min=1,max=1` free → radio + required; Add-ons =
`min=0,max=N` priced → chips (today's behaviour, unchanged).

## 3. Reusability — three scopes (the foodcourt differentiator)
A group's `owner` decides how far it's shared. Three tiers, increasing reach:

1. **Item-only** — defined inline on one item (the simplest; today's mental model). Owner = the item.
2. **Tenant library** — owned by a **merchant/storefront** (`merchant_id`), attachable to *any* of that
   tenant's items/outlets. e.g. a noodle stall reuses its "Dry/Soup" on 8 dishes. *(MVP target.)*
3. **Operator / foodcourt library — REUSABLE ACROSS STALLS.** Owned **above the tenant** (the venue/
   foodcourt node, or the platform operator = FSG). FSG curates **"Chilli level"**, **"Kopi sugar"**,
   **"Dry/Soup"** ONCE; each independent stall **attaches** the shared group to its items (opt-in).
   Resolves like the module flags / service options — by org-tree position. *(Phase 2 — the pitch win:
   consistent "mai hiam" wording + analytics across all 32 stalls, which single-tenant POS can't do.)*

**Why tier 3 matters for FSG:** the stalls are independent tenants (privacy/settlement), so a shared
preference library can only live **above** them — exactly where CIP's member-tree already sits. Operator
curates the vocabulary; stalls keep their own menus. (Same shape as the locked service-options cascade.)

## 4. Selection + UI
- **`CustomiseSheet`** — render each attached group in `sort_order`: `max_select=1` → **radio** (+ a
  "Required" tag, default-selected if `is_default`); `max_select>1` → **chips** (today). **Validate**
  required groups before "Add to cart". Live price = Σ chosen `price_delta`.
- **Menu editor** (`/merchant/menu`) — per item: **"Preferences & add-ons"** → create an inline group,
  OR **attach a shared group** from the tenant/operator library. A separate **library manager** (Ordering
  section) to define reusable groups (tier 2/3).
- **KDS / receipt** — the chosen options already print under each line (`OrderItem.modifiers` JSON snapshot,
  built today) — a Dry vs Soup choice shows on the kitchen ticket so the cook makes it right.

## 5. Order capture (mostly already there)
`OrderItem.modifiers` is a **JSON snapshot** (`[{name, price_delta}]`) taken at order time — unchanged; it
already carries whatever options were chosen, so KDS/receipt/void/reporting need no rework. Only the
*selection model + validation* change. `order` flow still funnels through one `record_sale()` (Foundation #6).

## 6. Build plan (phased — when approved)
- **P1 (tenant groups):** `MenuModifierGroup` + `MenuModifierOption` (migrate existing flat `MenuModifier`
  → one default group per item, back-compat) + `MenuItemModifierGroup` join + migration · menu-editor groups
  UI · `CustomiseSheet` radio/required + validation · `QrOrderCreate` validates required groups server-side.
- **P2 (operator/foodcourt library):** group `owner` = venue/operator node + cascade resolve +
  stall attach UI + a curated **Malaysia Boleh!** seed (Chilli Pan Mee w/ Dry/Soup + Chilli; Kopi w/ O/Peng/
  sugar) for the demo.
- **Later:** per-option availability (86'd items), price by option already supported.

## 7. Foundation Contract alignment
- **#5** resolver keys off the seller (stall/menu), not the group — groups attach via join, reusable.
- **#6** one `record_sale()`; options are a snapshot on the line, not a fork.
- **#7** the shared library is a capability that resolves by org-tree position (like module flags / service
  options) — additive, no rebuild.

## Net
Add **modifier GROUPS** with select rules (required, single/multi) so the menu speaks the diner's language
(Dry/Soup, mai hiam). Make groups **reusable** — item → tenant → **operator/foodcourt library** — so an
operator like **FSG curates one preference vocabulary across all 32 Malaysia Boleh! stalls**: the consistency
+ cross-stall analytics that a single-tenant POS structurally cannot offer. → memory `menu-modifier-groups`;
related `architecture-fulfilment-modes.md` (same cascade shape), `kpmg-foodcourt-deal.md`.
