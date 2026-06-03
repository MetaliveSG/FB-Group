# BreadTalk Group — member-tree (Chain/Storefront) + node-RBAC proof

Proof that the member tree supports **unlimited depth** with two node kinds — **Chain** (structural,
nests; may *stop the chain*) and **Storefront** (sells, the leaf) — and that **authority assigned at
any node cascades DOWN its subtree** (downline), never to siblings or upline. Real-shape BreadTalk
Group: a top **Chain** (the loyalty domain) over **two tenant Chains** (settlement boundaries =
"merchants"), depth 0→4, 15 nodes, 7 storefronts.

- `proof.txt` — the member-tree + every account's effective reach (generated output)
- Seed: `app/seed_breadtalk.py` (`build_breadtalk(db)`, idempotent insert+update+remove) ·
  Tests: `app/tests/test_breadtalk_member_tree.py` (12)

### LIVE per-level login proof (against the running Docker stack)
- `login_proof.py` — logs in as **all 10 accounts** (group Chain → Storefront) against
  `http://localhost:8000`, pulls each one's `GET /org/tree` + `/org/permissions`, and asserts a parent
  sees ALL its children with the right manage rights. Run: `python3 login_proof.py`. Writes `proof.txt`
  + `login_proof.json`. Checks: CEO (Manager @ top Chain) sees all 7 storefronts / both tenants /
  manages all; CFO (Finance) sees the whole group view-only; Chain managers isolated to their branch;
  a Storefront's Cashier/Staff scoped to that one storefront; Din Tai Fung sees nothing from BreadTalk.

### Operator merchant directory = member-tree drill-down
The operator console **Merchant Directory** is a member-tree navigator (driven by `GET /org/tree`).
Top level lists the top **Chain** (BreadTalk Group) + standalone merchants; clicking **zooms DOWN**:
`All merchants › BreadTalk Group › BreadTalk (F&B) Pte Ltd › <chain> › <storefront>`, breadcrumb to
climb back. Tenant Chains (settlement boundaries) keep their live KPIs + suspend/Enter/edit.
Screens: `screens/9-directory-1-toplevel.png` · `9-directory-2-enterprise-zoom.png` (the two tenants)
· `9-directory-3-merchant-zoom.png` (chains under BreadTalk F&B). Capture: `node screens_directory.mjs`.

- `screens/` — Org-Tree console screenshots for 8 levels (`screens.mjs`, Playwright):
  `1-group-chain-manager` (whole group, every Chain has "+ Add child") · `2-group-finance-readonly`
  (whole group, "View only", no add) · `3-tenant-chain-manager` (only BreadTalk F&B) ·
  `4-chain-toastbox` · `5-chain-foodrepublic-foodcourt` (chain-stopped, 3 storefronts) ·
  `6-storefront-ion` · `7-storefront-staff-chickenrice` · `8-chain-dintaifung-tenant2` (isolation).

## What it proves
| Account (role @ node) | Effective reach |
|---|---|
| **CEO / COO / CFO / Accountant** @ Enterprise | **both** Merchants, **all** outlets (whole group) |
| **Brand Manager** @ Toast Box | only Toast Box's outlet — not sibling brand BreadTalk, not the other Merchant |
| **Area Manager** @ Food Republic | only Food Republic's outlet |
| **Outlet Manager** @ ION | only that outlet |
| **Stall Operator** @ Chicken Rice | scopes to the stall's parent outlet |
| **Brand Manager** @ Din Tai Fung (Merchant 2) | only Merchant 2 — cross-merchant isolation within the group |

## How it works (no new tables, no migration)
- **Spine** (`org_nodes`): generic `Node` + `parent_id` + materialised `path` — depth-agnostic;
  reads are path-prefix `LIKE` (no recursion). BreadTalk seeded directly into the spine.
- **Node-scoped RBAC**: a role assigned at `scope_type=node, scope_id=<org_node>` cascades via
  `org_tree.grants_for_node()` → `(merchant, outlets)` grants over the node's subtree
  (Enterprise → every Merchant beneath; a node within a Merchant → that Merchant, limited to the
  outlets in its subtree). Wired into `auth/access.py::resolve_scope`.
- **Roles** = permission bundles (Group CEO/COO/CFO/Accountant, Merchant Owner, Brand Manager,
  Area Manager, Outlet Manager, Stall Operator, Staff); the **node** decides reach.

Demo logins (all `Password123!`): `ceo@breadtalk.sg`, `cfo@breadtalk.sg`, `bm.toastbox@breadtalk.sg`,
`am.foodrepublic@breadtalk.sg`, `om.ion@breadtalk.sg`, `stall.chicken@breadtalk.sg`, `bm.dtf@breadtalk.sg`.

## Live in the Docker stack + the Org-Tree console (build-the-tree UI)
- **Seeded into Postgres** by the stack: `SEED_BREADTALK=1` in `infra/docker-compose.yml` →
  `scripts/start.sh` runs `python -m app.seed_breadtalk` after migrations (idempotent upsert-by-id).
- **Browse + grow it** at `http://localhost:3001/merchant/org-tree` (log in at `/merchant/login`).
  The page is scope-aware (no `merchant_id`): the **CEO sees the whole group**, a **Brand Manager
  sees only its own subtree** — downline-only, never a sibling or the upline. Authorized roles get
  a **+ Add child** on any node they manage, creating nodes at **any depth** (Enterprise→Stall).
- **Endpoints** (key off `Scope.node_ids` / `manage_node_ids`, gated by the new `org.manage` perm):
  `GET /org/tree` · `POST /org/nodes {parent_id, role, name}` · `PATCH /org/nodes/{id}`.
  `OrgNode.name` (new column, migration `q4r5orgnodename`) carries the display label so pure-spine
  nodes (an Enterprise above the typed Merchant tables) render without a profile row.
