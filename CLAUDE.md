# CLAUDE.md — working notes for this repo

FB Group: a Singapore F&B CRM / QR-ordering / loyalty PoC. Project overview and the
capture-loop diagram live in `README.md`. This file is operating guidance for Claude.

## Stack
- **Backend** `apps/api` — FastAPI + SQLAlchemy 2.0 (typed `Mapped`/`mapped_column`) + Alembic.
  Own Python venv at `apps/api/.venv` (NOT in the JS workspace). PyJWT HS256, bcrypt direct.
- **Frontend** `apps/web` — Next.js 14 App Router, `(customer)` + `(merchant)` route groups,
  SVG charts, **no Tailwind**. Vitest for tests.
- **Shared** `packages/` — `api-client` (typed client, alias `@fbgroup/api-client`), `ui`, `types`, `config`.
- **DB** — Postgres 16 in Docker for prod-like; **SQLite for pytest** (in-memory, StaticPool,
  `Base.metadata.create_all` — tests do NOT run through Alembic). Same ORM code both ways.
- **Infra** `infra/docker-compose.yml`; **not a git repo** — "save progress" = files on disk + memory, never commits.

## Run & test
```bash
# Backend (fastest, SQLite):
cd apps/api && .venv/bin/python -m app.seed && .venv/bin/uvicorn app.main:app
cd apps/api && .venv/bin/python -m pytest          # backend tests
# Re-seed the SG-local merchant against live Postgres (idempotent, safe, no data loss):
cd apps/api && .venv/bin/python -m app.seed_kampong
# Full stack (Postgres + API + web):
docker-compose -f infra/docker-compose.yml up --build
# Frontend:
cd apps/web && npm install && npm run dev      # dev
cd apps/web && npm run test                    # Vitest
```
Baseline: **157 backend + 45 frontend tests pass** · 93 endpoints · 41 tables · 13 migrations.

## Environment gotchas (this machine)
- Docker CLI is **`docker-compose`** (hyphenated v1), NOT `docker compose` v2.
- Web is mapped to host **:3001** (host 3000 was taken); API on :8000; Postgres on :5432.
  API CORS allows both 3000 + 3001. API `DEBUG=true` in compose → OTP returns `debug_code`.
- DB creds (compose): user/pass/db all `fbgroup`. Connect tools to `localhost:5432`.

## Conventions & traps
- **Multi-tenant**: nearly every query is scoped by `merchant_id`. Lead with it in any composite index.
  Operator (super_admin) drills into merchants via `?merchant_id=`.
- **Money** = `Numeric(12,2)` as Python `Decimal`. **PKs** = `String(32)` hex UUID (`uuid4().hex`).
  **Timestamps** = naive UTC (`app/db/base.py::utcnow`); SG is UTC+8.
- **VARCHAR length**: SQLite tests do NOT enforce it; Postgres does. A value that fits in SQLite
  can 500 on Postgres (bit us once with a voucher code in `reward_redemptions.status`). Verify on PG.
- **Alembic migrations target Postgres natively** (plain `op.create_table`); they can't run on SQLite.
- **api-client types can claim fields the backend schema doesn't return** — TS compiles, runtime crashes,
  and only on the non-empty path. Keep `packages/api-client` types in sync with `app/schemas`.
- **Idempotent seed pattern**: `seed_kampong` / `_ensure_kampong_jackpot` do insert+update+remove keyed
  by stable name (with an empty-seed guard). "Edit the seed → re-run → live reflects it", no migration.
- **Provider mocks** (OTP / WhatsApp / AI insights): mock by default; real provider only when a flag +
  key are set (e.g. `AI_ENABLED=1` + `ANTHROPIC_API_KEY`). Tests/demo use the deterministic mock path.

## Where things are
- `apps/api/app/models/*.py` — schema (source of truth) · `app/services/` — business logic (ORM only, no raw SQL)
- `app/analytics/` — read-heavy paths (`reports.py`, `rfm.py`, `crm.py`) · `app/loyalty/engine.py` — hot accrual path
- `docs/` — `delivery-report.md` (canonical current state), architecture/api/database/security/testing/deployment/bc-dr/PRD
- `artifacts/` — generated proofs (openapi.json, pytest_results.txt, sample JSON, demo_credentials.md)
- `queries/` — ready-to-run diagnostic SQL (run via SQLTools or `psql -f`); see header in `01_customer_lookup.sql`
- `.vscode/` — SQLTools connection to the Docker Postgres + recommended extensions

## Demo credentials
- Operator: `http://localhost:3001/operator/login` → `superadmin@platform.sg` / `Password123!`
- Merchant owner: `http://localhost:3001/merchant/login` → `owner@makan.sg` (or `owner@kampongeats.sg`) / `Password123!`
- Customer QR: `http://localhost:3001/t/orchard-01` (or `kampong-bedok-01`); OTP phone `+6580000000` (DEBUG returns the code)
- QR tokens are **stable slugs** (per outlet+table) that survive reseeds.

## Memory & skills
- Persistent memory: `~/.claude/projects/-Volumes-Data-Drive-Coding-multi-agent-FB-Group/memory/`
  — `MEMORY.md` index + `build-state.md` (canonical Round log + KIVs), `project-fbgroup-crm.md`, `arch-decisions.md`, `user-prefs.md`.
  Run `/my-catchup` at session start; `/my-wrapup` to close out (updates memory + regenerates artifacts).
- Project skills in `.claude/skills/`: `/my-architect`, `/my-tester`, `/my-security-audit`, `/my-dba`,
  `/my-ops`, `/my-diagnose`, `/my-bizdev` (advisors) + `/my-catchup`, `/my-wrapup` (lifecycle).

## How the user works (Founder Mode)
~2-person team + Claude Code. Prioritize speed, working+tested software, revenue/adoption — while keeping
strong security/testing/architecture standards. Be decisive; prefer prose planning over multiple-choice
prompts. Don't claim completion without passing tests + proof of the demo flow.
