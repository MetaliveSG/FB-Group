# BreadTalk Group — unlimited member-tree + node-RBAC proof

Proof that the org tree supports **unlimited depth** and that **authority assigned at any node
cascades DOWN its subtree** (downline), never to siblings or upline — using a real-shape
BreadTalk Group (an **Enterprise** spanning **two Merchants**, depth 0→4, deeper than the typed
chain's 3).

- `proof.txt` — the member-tree + every account's effective reach (generated output)
- `demo.py` — regenerate it: `cd apps/api && PYTHONPATH=. .venv/bin/python ../../artifacts/breadtalk-member-tree/demo.py`
- Seed: `app/seed_breadtalk.py` (`build_breadtalk(db)`) · Tests: `app/tests/test_breadtalk_member_tree.py` (7)

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
