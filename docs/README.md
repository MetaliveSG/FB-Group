# docs/ — map & status

**Read `decisions.md` first** — the decision register is the authority on what's currently decided;
it outranks any doc's narrative when they disagree. Status tags below: **AS-BUILT** (describes shipped
reality) · **PARTIAL** (some built, some plan — read the doc's own header) · **PLAN** (designed, NOT
built — don't cite as reality) · **REFERENCE** (positioning/collateral, not code) · **SUPERSEDED**
(historical, in `archive/`). Ground-truth counts live in `delivery-report.md` + the regenerated
`artifacts/` (openapi.json, pytest_results.txt, schema_tables.txt) — trust those over doc prose.

## Authority & state
| Doc | Status | What it is |
|---|---|---|
| `decisions.md` | ⭐ REGISTER | One row per firmed decision (LOCKED/AGREED/DEFERRED/SUPERSEDED) — append in the turn a decision is firmed |
| `delivery-report.md` | ⭐ AS-BUILT | Canonical current-state rollup (counts, features, creds, limitations) |
| `SESSION_NOTES.md` | JOURNAL | Human-readable session log (newest first; started 2026-06-08) |

## Architecture
| Doc | Status | What it is |
|---|---|---|
| `architecture.md` | AS-BUILT | System overview (modular monolith, 4 surfaces) |
| `architecture-org-tree.md` | PARTIAL | Member tree: §12 AS-BUILT (the spec to trust) · §10 leasing BUILT · §1–9 plan-first |
| `architecture-3-modules.md` | PARTIAL | Table QR · Intelligence · POS: Phase A BUILT, B–F plan |
| `architecture-fulfilment-modes.md` | AS-BUILT | Two-axis service options (dining context × hand-off) + KDS — built R42 |
| `architecture-scan-domains.md` | AS-DECIDED | `{slug}.mycip.io` QR domain scheme (LOCKED; slug/resolver not built) |
| `architecture-vouchers.md` | AS-BUILT | Voucher core, two issuers, one redemption (tiers 1–2) |
| `architecture-pos-mvp.md` | AS-BUILT | Staff POS (all 7 slices; as-built deltas in §Status) |
| `architecture-unified-console.md` | PARTIAL | One tree-scoped console: Stage 1 built, 2–4 plan |
| `architecture-modifier-groups.md` | PLAN | Menu preference groups (Dry/Soup, chilli, kopi sugar) — not built |
| `reporting-timezone.md` | AS-BUILT | One-tz-per-report design (Phases 1–2 built, 3 KIV) |
| `roadmap-network-loyalty.md` | PARTIAL | Menu+foodcourt phases BUILT; FX network deferred |
| `buildplan-land-first.md` | PLAN | LAND-tier counter-QR SKU build plan (not started) |

## Engineering reference
| Doc | Status | What it is |
|---|---|---|
| `api.md` | AS-BUILT | Endpoint reference |
| `database.md` | AS-BUILT | Schema overview (tables by domain) |
| `testing.md` | AS-BUILT | Test counts + coverage map |
| `security.md` | AS-BUILT | Auth/RBAC/tenancy security posture (highest-fidelity doc) |
| `deployment.md` | PARTIAL | Local/migrations AS-BUILT; AWS blueprint ASPIRATIONAL (no IaC exists) |
| `bc-dr.md` | PARTIAL | PoC backup/restore AS-BUILT; production BC/DR aspirational |
| `product-requirements.md` | PLAN | Requirements baseline (status → delivery-report §5) |
| `poc-demo.md` | REFERENCE | 12-min pitch script (seed first — clean boot) |

## Business / GTM (collateral, not code)
| Doc | Status | What it is |
|---|---|---|
| `positioning.md` | REFERENCE | CIP pitch · land-and-expand · growth model |
| `cip-vs-salesforce-fnb.md` | REFERENCE | Competitive collateral (KPMG deal) |
| `foodcourt-pilot-kit.md` | REFERENCE | Foodcourt pilot collateral |
| `fsg-chairman-deck.md` | REFERENCE | FSG chairman deck source |
| `payments.md` | PLAN | ⭐ Real payment, consolidated 2026-06-12: HitPay PSP + build spec + FSG wallet (§7) + uPOS integration (§8) — the pilot critical path |

## archive/
Superseded docs kept for the paper trail — do not cite as current:
- `archive/implementation-phases.md` — pre-build phase plan (2026-05-31); roadmap authority is now
  CLAUDE.md + memory `roadmap-mvp-foundation`; its Phase 3 (external-POS API) conflicts with the
  locked no-external-POS-in-MVP decision.
