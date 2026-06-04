# Unified Tree-Scoped Console — design (FOR SIGN-OFF, not yet built)

**Status:** proposed 2026-06-04 · supersedes the split `/platform` (operator) + `/merchant/*`
(tenant) consoles · MVP definition-of-done item. As-built spine reference: `architecture-org-tree.md §12`.

## 1. The principle

**One console. Your identity grants you a *position* in the member tree (a scope root) and a
*cascade* of permissions. Every page renders relative to your current scope.** The platform operator
is simply the user whose scope root is the **tree root** — above all tenant boundaries. A chain owner's
root is their chain; a storefront manager's root is their storefront. The nav is constant; pages adapt
to where you stand. Features **scope downward**: reports, onboarding, QR menu, "Enter", orders,
tables & QR all aggregate or drill from your current node.

This is not a new concept bolted on — it is the **member-tree moat (M3) finally expressed in the UI**:
*authority = tree position × cascade* ([[member-tree-chain-storefront]]).

## 2. Why the split console breaks today (the bug this fixes)

There are two scoping models behind two front doors:
- **Merchant-staff login** → the JWT carries the merchant; every `/merchant/*` page self-scopes.
- **Operator login** → has *no* implicit merchant; scope exists **only** after "Enter" sets the
  `getOperatorMerchant()` context (localStorage).

Every `/merchant/*` page sends `merchant_id = getOperatorMerchant()?.id`. **Reports is the lone
exception** — it has explicit platform-aggregate logic (operator + no context → `{platform:true}`,
`merchant_id=null` aggregates the subtree). So the Platform "📊 Reports" button *clears* the context
and lands the operator in the merchant shell, where Reports works but **the other 11 nav links send
`merchant_id=undefined` → the backend rejects (an operator must name a merchant) → "missing merchant
id".** 1 of 12 links works. The root cause: per-tenant pages have no notion of "scope above a tenant."

## 3. Core abstraction — `Scope`

A scope is a *position in the tree*, derived from the user's grant + where they've navigated:

```ts
interface Scope {
  rootNodeId: string;            // grant ceiling: deepest node the user may ascend to (operator = ROOT sentinel)
  currentNodeId: string;         // current focus; "Enter" descends, breadcrumb ascends (bounded by rootNodeId)
  kind: 'platform' | 'chain' | 'tenant' | 'storefront';  // derived from current node's flags
  tenantId: string | null;       // nearest ancestor-or-self that is a settlement/loyalty boundary; null if ABOVE all boundaries
  outletId: string | null;       // set iff currentNode is a single Storefront leaf
}
```

- `kind='platform'` — at/near root, **above all tenant boundaries** (`tenantId === null`).
- `kind='chain'` — a structural node; may be a cross-tenant group (spans several boundaries) **or** a
  sub-chain *within* one tenant.
- `kind='tenant'` — the current node **is** a settlement/loyalty boundary (a "merchant").
- `kind='storefront'` — a `sells=true` leaf.

`tenantId` = the nearest settlement/loyalty-boundary ancestor-or-self. If none → you are above all
tenants → per-tenant pages show a directory, not data. This is the single field that fixes the bug.

**Front-end contract:** a `useScope()` hook (apps/web `lib/`) returns the `Scope` + `enter(nodeId)` /
`ascendTo(nodeId)`. It generalises the existing `OperatorMerchant` localStorage context: store
`{ currentNodeId }`, derive the rest from the loaded `org/tree` + caps. Client-only → **mount-gate**
(SSR/hydration lesson). On load, validate `currentNodeId` against the freshly-loaded tree (a node may
have been deleted/re-parented) → fall back to `rootNodeId`.

## 4. The page-tier rule (what "scope down" means per page)

Each route declares a **tier**. A `<ScopedPage tier=…>` wrapper reads `useScope()` and decides what to render:

| Tier | Pages | Behaviour as you scope down |
|---|---|---|
| **structural** | org tree · onboard node · Enter · QR provision | Operate on `currentNode`'s **subtree** at *any* node. |
| **rollup** | Reports · dashboards · order *counts* | **Aggregate the whole subtree** below `currentNode` (Reports already does this; `merchant_id=null` + subtree outlets for cross-tenant groups). |
| **tenant-op** | CRM · orders list · settings · menu · tables & QR | Bound to the **tenant boundary**. `tenantId != null` ⇒ operate, scoped to that tenant (+ optional sub-storefront filter from `currentNode`). `tenantId == null` (above all boundaries) ⇒ render a **NodeDirectory** ("pick a merchant under <currentNode>") — **never call the API with a null merchant_id**. |

The third row is the crux and it **honours the existing rule** (`CLAUDE.md`: *CRM/Orders/Settings stay
tenant-wide — the loyalty ring is the tenant*). A regional manager does not scroll one cross-merchant
customer list; they pick a store and drill in. Cross-tenant CRM merging is a **coalition** feature
(separate), never an accidental "show all".

**Scope stops, two directions:**
- Per-tenant pages **don't scope BELOW** the tenant boundary (CRM/loyalty are tenant-wide; a sub-chain
  shares the tenant's customer ring). Menu/Tables *do* sub-scope (filter to `currentNode`'s subtree).
- Per-tenant pages **don't aggregate ABOVE** the boundary → directory instead.

## 5. The shell merge

- `/platform` and `/merchant/*` unify under **one layout**: (a) a **breadcrumb / scope switcher** in the
  top bar — `Platform ▸ Chain ▸ Tenant ▸ Storefront`, current node highlighted, segments clickable to
  ascend (bounded by `rootNodeId`); (b) the constant left nav; (c) a **scope banner** (replaces the
  one-way operator-view banner — now shows "Platform view — pick a node" when `tenantId == null`).
- Today's `/platform` directory becomes the reusable **NodeDirectory** component (also used by tenant-op
  pages when above a boundary).
- **"Enter"** sets `currentNodeId` (descend). Breadcrumb segments ascend. Both bounded by the grant.

## 6. Backend (mostly already built this session)

- Rollup endpoints accept `node_id`, aggregate the subtree — **done** (`reports.py::_scope`).
- Tenant-op endpoints: when handed a node **above** a tenant boundary, return a **structured 409**
  (`scope_above_tenant_boundary`) instead of an opaque "missing merchant id" 400, so the UI can render
  the directory even if it ever reaches the API. (UI prevents the call; API stays honest.)
- Enforce `currentNodeId ∈ visible_nodes(scope)` → 403 upline (**already server-enforced** via
  `org_tree.grants_for_node`). RBAC model is unchanged: grant = ceiling, UI hides what's not granted,
  operator = root grant.

## 7. Staged rollout — suite-green each stage, never regress the merchant self-scoped login

1. **Scope foundation** — `useScope()` + `<ScopedPage>` wrapper + `NodeDirectory`. Per-tenant pages stop
   calling the API with a null merchant_id; render the directory when `tenantId == null`. **This stage
   alone kills the bug** — no shell change yet. *(demo-protecting; smallest safe slice)*
2. **Shell merge** — breadcrumb/scope-switcher; `/platform` rehosted as the root-scope landing of the
   *same* console; scope banner.
3. **Scope-down everywhere** — onboard-at-any-node, orders rollup-with-drill, tables/QR at leaves;
   structural + rollup pages scope-aware at every node.
4. **Polish** — RBAC-driven nav hiding, retire the old split routes, e2e both personas.

## 8. Risks / edge cases

- **Cross-tenant group** (the `CEO@btg` case already fixed): rollup must aggregate across *multiple*
  tenant boundaries (`merchant_id=null` + subtree outlets). The model formalises it.
- **Sub-chain-within-a-tenant grant**: tenant-op pages scope to the tenant boundary (CRM tenant-wide),
  while menu/tables sub-scope to `currentNode`. `Scope` must expose **both** `tenantId` and the
  `currentNode` subtree.
- **Breadcrumb must not ascend above the grant ceiling** (`rootNodeId`).
- **Stale localStorage scope** → validate against the loaded tree each mount; fall back to `rootNodeId`.
- **SSR/hydration** → scope reads localStorage → mount-gate (no scope-dependent render on the server).

## 9. Why not literally "operator login → the merchant UI"?

Because **most merchant pages are inherently single-tenant** (CRM, orders, settings, menu, team). A
naive merge just spreads "missing merchant id" to 11 pages. The fix is *scope-awareness* (tier the
pages), not page reuse alone. The shell is shared; the **per-tenant pages gain a "you're too high — pick
a node" state**, which is also their natural rendering at Platform scope. Same code, correct semantics.
