# Architecture

## Overview
A modular-monolith FastAPI backend serves every client (customer web app, merchant
CRM, operator console, and future POS/ordering apps) over one versioned REST API
(**109 endpoints, 41 tables**). State lives in PostgreSQL via SQLAlchemy 2.0; Alembic
manages schema (13 migrations). The Next.js frontend (App Router, **22 routes**) serves
three personas: **customer** (`/t/[token]`, rewards), **merchant** (CRM, AI insights,
pipeline, campaigns, RFM, menu/team/org/settings admin), and **operator** (`/operator`).

```
                ┌────────────────────────── apps/web (Next.js) ─────────────────────────┐
                │  (customer) QR order flow        (merchant) CRM dashboard + reports     │
                └───────────────┬───────────────────────────────┬─────────────────────────┘
                                │  HTTPS / JWT                    │
                       ┌────────▼─────────────────────────────────▼────────┐
                       │             FastAPI  (apps/api)                    │
                       │  routes → services → repositories/models           │
                       │  domains: tenancy · auth · catalog · orders ·       │
                       │  payments · loyalty · crm · campaigns · analytics · │
                       │  engagement(pipeline/activities/rewards) · platform │
                       │  cross-cutting: RBAC/scope · rate limit · audit ·   │
                       │  secure headers · structured logging                │
                       └────────┬───────────────────────────────────────────┘
                                │ SQLAlchemy 2.0 / Alembic
                          ┌─────▼─────┐
                          │PostgreSQL │   (SQLite for dev/tests — same ORM code)
                          └───────────┘
```

## Why a modular monolith
Single deployable, one transactional database, simplest possible operational
surface for a 2-person team — while staying **domain-modular** so any module can be
extracted into a service later if load demands. POS and a richer ordering app are
*additional clients of the same API*, not rewrites: building the CRM correctly
already lays ~70% of the POS backend (catalog, orders, payments, customers, loyalty).

## Multi-tenancy
Hierarchy: `Merchant → Brand → Outlet → Table → QRCode`. `merchant_id` is
denormalized onto descendant + transactional rows so **tenant isolation is a single
indexed predicate** on every query. Authorization resolves a user's role
assignments (platform / merchant / brand / outlet scope) into an effective `Scope`
(`app/auth/access.py`) that gates both endpoint permissions and row-level visibility
(e.g. an outlet manager only sees customers who transacted at their outlet).

## Identity model
Two identity tables by design: **`users`** (back-office: super admin → staff,
password + scoped roles) and **`customers`** (diners; one or more
`customer_auth_identities`: password / mobile-OTP / Google / Apple). A customer is a
global person (enables coalition + account linking); a merchant's CRM "customers" are
those holding a merchant-scoped `loyalty_account` (created on first transaction).

## Request lifecycle (capture loop)
`GET /qr/{token}` → resolve context + menu → customer auth (JWT) →
`POST /orders` (server prices items, prevents tampering) →
`POST /orders/{id}/checkout` (simulated payment → `transactions` ledger row →
loyalty engine accrues points) → CRM reads derive metrics/segments on demand.

## Loyalty engine (`app/loyalty/engine.py`)
Rule-driven, never hardcoded: `reward_rules` rows hold JSON config for earn-rate,
first-visit, birthday, repeat-visit, and campaign-multiplier. Accrual writes an
append-only `reward_transactions` ledger and updates the account
(balance/lifetime/tier/visit dates). Merchant-isolated and coalition rewards are
separate scoped accounts.

## Analytics (`app/analytics/`)
CRM metrics (lifecycle, churn risk, 8 segments) and sales reports/forecast are
computed on demand from the ledger — no stale denormalized state. Forecast is a
documented naive moving average (PoC).

## AI Insights advisor (`app/services/ai_insights.py`)
An "ask-your-business" layer on top of the analytics: it gathers a compact context
(sales totals + 30-day momentum, forecast, top items, CRM segments, churn, RFM,
pipeline, campaign performance) and returns an executive summary plus ranked,
feature-linked next-best actions (win-back launcher, segment campaigns, pipeline
follow-up). A **provider abstraction** mirrors the OTP/WhatsApp/payment mocks: with
`AI_ENABLED=1` + `ANTHROPIC_API_KEY` it calls **Claude** (Anthropic SDK; cached system
prompt, structured-JSON output); otherwise — and on any API failure — it falls back to
a **deterministic heuristic** advisor, so the PoC demos with no key and tests stay
reproducible.

## Key decisions
- **SQLite for dev/test, Postgres for prod** — identical SQLAlchemy 2.0 code; tests
  run anywhere with zero setup.
- **Money as `Decimal`** (Numeric(12,2)), banker-safe rounding — never float.
- **JWT (PyJWT HS256)** access + refresh; bcrypt password hashing.
- **OpenAPI is the source of truth** for the typed `packages/api-client`.
