# FB Group — Singapore F&B CRM / QR Ordering / Loyalty Platform (PoC)

Merchant-first F&B retention infrastructure. A diner scans a table QR, logs in,
orders, checks out (simulated payment), earns loyalty points — and is instantly
**captured and profiled in the merchant CRM** (lifecycle, spend, frequency,
churn risk, segments). Multi-tenant, role-scoped, with sales reports + forecasts.

```
Customer (web app)                                  Merchant (CRM)
─ scan QR ─ login ─ order ─ pay ─ earn points ──►  customer profiled + segmented
```

**Org model — the Chain/Storefront *member tree*.** Merchants are onboarded and managed as a single
tree of two node kinds — **Chain** (structural; nests) and **Storefront** (the selling leaf) — from
the **Platform Console** (`/platform`). Creating a Storefront auto-provisions its outlet, menu and QR;
**Enter** any node for a console scoped to its subtree. Full as-built spec:
[`docs/architecture-org-tree.md` §12](docs/architecture-org-tree.md).

## Monorepo layout
```
apps/api      FastAPI + SQLAlchemy 2.0 + Alembic   (the verifiable core; 230 tests)
apps/web      Next.js (customer QR flow + merchant CRM)
packages/     api-client (typed), ui, types, config
infra/        docker-compose, Dockerfiles
docs/         architecture, api, security, testing, deployment, bc-dr, PRD
artifacts/    test output + generated JSON proofs
```

## Run it

### Option A — Backend only, zero-setup (SQLite). Fastest; this is what the tests use.
```bash
cd apps/api
python3 -m venv .venv && . .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.seed                 # build demo data (SQLite ./fbgroup.db)
.venv/bin/uvicorn app.main:app --reload      # http://localhost:8000/docs
.venv/bin/python -m pytest                    # 230 tests
```

### Option B — Full stack with Postgres (Docker)
```bash
docker compose -f infra/docker-compose.yml up --build
# api: http://localhost:8000/docs   web: http://localhost:3001
# API container runs Alembic migrations; demo seeding is OFF by default (SEED_ON_START=0) —
# onboard merchants via the Platform Console (/platform), or set SEED_ON_START=1 for the demo dataset
```

### Frontend dev (local)
```bash
cd apps/web && npm install && npm run dev   # http://localhost:3000
# point NEXT_PUBLIC_API_BASE at the API (default http://localhost:8000)
```

## Demo credentials
Staff password `Password123!` · customer password `Customer123!` (or OTP).

| Role | Email |
|------|-------|
| Super Admin | superadmin@platform.sg |
| Merchant Owner (Makan Express) | owner@makan.sg |
| Outlet Manager (Orchard) | manager.orchard@makan.sg |
| Staff/Cashier (Orchard) | staff.orchard@makan.sg |
| Merchant Owner (Kopi Culture) | owner@kopiculture.sg |

The sample QR token is printed by `python -m app.seed` and saved to
`artifacts/demo_credentials.md`.

## Docs
[Architecture](docs/architecture.md) · [API](docs/api.md) · [Security](docs/security.md) ·
[Testing](docs/testing.md) · [Deployment](docs/deployment.md) · [BC/DR](docs/bc-dr.md) ·
[PRD](docs/product-requirements.md)
