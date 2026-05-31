# Implementation Phases — Org Tree, Loyalty Ledger, POS & ERP-readiness

> Status: **plan agreed, not yet built** (captured 2026-05-31).
> The build sequence to fulfil the requirements in `architecture-org-tree.md` (structure) and
> `roadmap-network-loyalty.md` (loyalty/FX economics). Sequenced by **irreversibility and
> dependency** — cheap-but-irreversible seams first, heavy structure pulled by real demand.
> Each phase keeps the current demo (single merchant = trivial tree) green throughout.

---

## Current-state scorecard

Grounded in a code review of the live backend (4 parallel area reviews, 2026-05-31).

| # | Requirement | Exists today | Gap | Effort |
|---|---|---|---|---|
| 4 | Append-only **domain-stamped ledger** | `RewardTransaction` append-only ✅; `points_balance` is a cache ✅ | no domain stamp on the txn row; no idempotency key | **S** |
| 6 | **Modular adoption** | `merchant.settings` JSON toggles exist | formalise `rewards/qr/pos` flags + gate behaviour | **S** |
| 3 | **Two boundaries** (loyalty vs settlement) | loyalty scope-abstracted to `(scope_type, scope_id)` ✅; settlement at merchant only | add `settlement_account_id` + per-venue `settlement_mode`; `LoyaltyDomain` first-class | **M** |
| 1 | **Org tree** (Node + flags + path) | typed tables + `merchant_id` denorm; Menu-as-stall; **no parent_id/path** | add `org_node` spine; typed tables become profiles | **L** |
| 2 | **3 read-paths + RBAC node cascade** | `require()`/`Scope` insulates ~48 sites; flat scope, no cascade | `node_id` on role assignment; rewrite `resolve_scope` to path-cascade; 9 filter sites | **L** |
| 7 | **POS integration API** | clean routers, provider-mock pattern, public/authed split | no API-key auth, no idempotency, no `external_id`, no webhooks, no `OrderChannel.POS` | **M** |
| 5 | **Value rollup engine** | `RewardRule.config` JSON extensible; per-rule attribution | 0% — per-node terms, rollup, caps, close | **L** |
| 8 | **Multi-domain + clearing fees** | scope seam present | domain entity + fee config + clearing postings + FX | **M** |

**Already-correct foundations** (why "ready for scale" is achievable without a rewrite):
append-only ledger · loyalty already `(scope_type, scope_id)`-abstracted · `points_balance` is a
cache not the truth · clean `require()`/`Scope` RBAC · `merchant_id` denormalised on all
descendants · `merchant.settings` JSON · Menu-as-stall foodcourt model.

---

## Phase 0 — Foundational seams · ✅ DONE (2026-05-31)

Behaviour-neutral; lays the irreversible bits so everything else is additive. Kept all
tests green (152 backend / 45 web at completion).

- **0a — Domain-stamp the ledger.** Add `loyalty_domain_id` to `RewardTransaction` (= `scope_id`
  today) + an **idempotency key**. Add an invariant test: `points_balance == SUM(ledger)`.
  *Frame the ledger as a generic **posting** substrate (not coin-only) — see ERP-readiness §9.*
- **0b — POS-ready order primitives.** `external_id` / `source_ref` on Order/Payment; an
  idempotency mechanism on `create_order`; `OrderChannel.POS`. *Treat `Order` as the first
  instance of a document + lines + workflow + postings pattern.*
- **0c — Module flags.** `rewards_enabled` / `qr_ordering_enabled` / `pos_enabled` in
  `merchant.settings` (record only; gate in Phase 2).
- **0d — Boundary indirection.** Introduce `loyalty_domain_id` + `settlement_account_id` as
  concepts that equal `merchant_id` today, so code stops reading `merchant_id` directly for
  those two purposes. Seed JSONB custom-field extensibility on core entities.
- **Handoffs:** `/my-dba` (ledger index + idempotency), `/my-tester` (reconciliation + idempotency).
- **Exit:** no behaviour change; suite green; the irreversible seams are in.

## Phase 1 — Org spine (Node + path) · ✅ DONE (2026-05-31) · the core scale move

- `org_node(id, parent_id, role, depth, path, sells, is_settlement_boundary, is_loyalty_domain,
  module flags, loyalty_domain_id, settlement_account_id, is_active)`.
- Backfill one node per Merchant/Brand/Outlet/Menu(stall); **typed tables stay as profiles**
  (`id == node id`); maintain `path`/`depth` on write.
- Generalise RBAC: `UserRoleAssignment.node_id`; rewrite `resolve_scope` to **cascade down the
  subtree** via path-prefix; `require()` signatures unchanged (~39 sites safe); convert the 9
  outlet-filter sites to path-containment.
- Uniform **resolution by context** (QR location / app network / POS operator) over the spine —
  the QR part is mostly built.
- **`/my-dba` decision:** materialised **varchar `path` + `LIKE 'x.%'`** (portable to the SQLite
  test path) vs **Postgres LTREE** (faster, PG-only). Lean varchar-path now; LTREE as a later
  PG-only optimisation.
- **Handoffs:** `/my-dba` (path indexing, live-PG migration), `/my-security-audit` (**P0** — the
  `resolve_scope` rewrite is the top cross-tenant-leak risk; isolation tests FIRST),
  `/my-tester` (two-world isolation + subtree cascade), `/my-ops` (deploy verify).
- **Exit:** validated against NTUC/BreadTalk + aircon/non-aircon fixtures before cutover.

## Phase 2 — Boundaries + modular gating live · ~1 week

- `settlement_account_id` + per-venue `settlement_mode` (operator vs per_stall); orders/payments
  settle to the resolved account. `LoyaltyDomain` first-class (default 1:1 with merchant).
- Module flags now **gate behaviour**: QR resolver branches (menu vs earn/rewards screen); POS
  roles + settlement exist only when `pos_enabled`.
- **Handoffs:** `/my-security-audit` (settlement scoping), `/my-tester`.

## Phase 3 — POS integration API · ~1–1.5 weeks

- `service_credentials` (API key scoped to a node subtree) + `get_api_key()` M2M dependency.
- Inbound `POST /api/v1/integrations/pos/...` (orders/sales/menu) with idempotency + `external_id`
  + HMAC signature; reuse `create_order`.
- Outbound webhooks: signed events (tickets, menu/price sync, reconciliation), retry via the
  existing `send_with_retry` pattern.
- **Handoffs:** `/my-security-audit` (**P0** — API-key auth, signature, key→subtree scoping),
  `/my-tester` (idempotent double-push, spoofed-key).

## Phase 4 — Multi-domain loyalty + rollup engine · ~2 weeks · pull when a franchise/cross-domain deal lands

- `org_node_terms` (per-node, fixed *or* %, kind/base/beneficiary, caps, effective-dated).
- Rollup engine: ancestor-walk via `path`, post to ledger; platform-fee vs royalty as config;
  periodic close over a frozen snapshot.
- Cross-domain redemption clearing fee + FX + breakage (NTUC↔BreadTalk).
- **Handoffs:** `/my-bizdev` (fee/FX economics), `/my-dba` (close performance), `/my-tester`
  (rollup correctness, caps).

---

## Risks to control

| Sev | Risk | Control |
|---|---|---|
| **P0** | RBAC `resolve_scope` rewrite (Ph1) → cross-tenant leak | two-world isolation tests written FIRST, watched to fail; `/my-security-audit` + `/my-tester` |
| **P0** | Ledger integrity (Ph0) | `loyalty_domain_id` stamped at mint, never mutated; invariant test `balance == SUM(ledger)` |
| **P1** | `path` on Postgres `VARCHAR(512)` | watch depth × key length; SQLite-passes/PG-fails trap (cf. `reward_redemptions.status` precedent); verify on live PG via `/my-dba` |
| **P1** | Idempotency (Ph0/3) | make it foundational in 0b/0a, not bolted on in 3 — a POS retry must not double-post |

---

## Build discipline

- **Foundational now (Phase 0):** cheap, irreversible-if-skipped, behaviour-neutral. Do it.
- **Phase 1** committed next (the spine) since "ready for this scale" is a stated goal — but run
  deliberately (isolation tests first, validate fixtures before cutover), never big-bang.
- **Phases 3–4 are demand-pulled:** POS integration when a merchant needs it; the rollup engine
  when a franchise / cross-domain deal is real.
- **ERP modules (inventory, GL, procurement, payroll):** build the backbone (generic posting
  ledger, document pattern, products, module flags, integration, custom fields — see
  `architecture-org-tree.md` §9); ship each module only when pulled. No speculative mega-model.
