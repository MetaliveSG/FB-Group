# Contributing

How we work now that the project is moving from PoC to a real development effort.
The goal: anyone can make a change safely, CI proves it, and `main` is always releasable.

## Branch & PR flow (no direct commits to `main`)

`main` is protected — all changes land via pull request.

```bash
git checkout main && git pull
git checkout -b <type>/<short-topic>        # e.g. feat/referral-program, fix/checkout-race
# ... make the change + tests ...
git push -u origin HEAD
gh pr create --fill                          # or open the PR in GitHub
```

A PR may merge when **all CI jobs are green** and it has one review approval.
Prefer **squash-merge** so `main` stays one logical commit per change.

> Enable branch protection on GitHub once: Settings → Branches → add a rule for `main`
> requiring the `Backend`, `Frontend`, and `Migrations` checks + 1 approving review.

## Commit messages (Conventional Commits)

`<type>(<scope>): <summary>` — `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`.
End the trailer with the Claude co-author line if AI-assisted.

## What CI checks (`.github/workflows/ci.yml`)

| Job | Runs |
|---|---|
| **Backend** | `ruff check app` + `pytest` (in-memory SQLite) — in `apps/api` |
| **Frontend** | `tsc --noEmit` + `vitest` + `next build` — workspaces installed via `npm ci` |
| **Migrations** | real Postgres: `alembic upgrade head` → `downgrade base` → `upgrade head`, then a **drift guard** (autogenerate must produce no schema ops). Catches model changes made without a migration — the parity pytest's SQLite path does not exercise. |

Run it all locally before pushing:

```bash
# backend
cd apps/api && .venv/bin/ruff check app && .venv/bin/python -m pytest -q
# frontend
npm ci && npx tsc --noEmit --project apps/web/tsconfig.json \
  && npm run test --workspace apps/web && npm run build --workspace apps/web
# migrations (against a scratch Postgres; see infra/docker-compose.yml for one)
cd apps/api && DATABASE_URL=postgresql+psycopg://fbgroup:fbgroup@localhost:5432/fbgroup \
  alembic upgrade head && alembic downgrade base
```

## Schema changes — always add a migration

Tests run on SQLite via `Base.metadata.create_all` and do **not** run Alembic, so a model
change without a migration is invisible to pytest but breaks Postgres. When you touch a
model:

```bash
cd apps/api
DATABASE_URL=postgresql+psycopg://fbgroup:fbgroup@localhost:5432/fbgroup \
  alembic revision --autogenerate -m "describe the change"
# review the generated file, then:
alembic upgrade head
```

The CI **Migrations** job fails if you forget (drift guard). Alembic targets Postgres
natively — generate/run migrations against Postgres, not SQLite.

## Pre-commit hooks (optional but recommended)

```bash
pip install pre-commit && pre-commit install
```

Runs ruff (autofix) + whitespace/EOF/yaml checks on staged files before each commit
(`.pre-commit-config.yaml`).

## Secrets

Never commit secrets. Local dev reads `.env` (see `.env.example`); CI uses GitHub Actions
secrets; production injects from a secrets manager. `JWT_SECRET`, DB URL, and provider keys
are all env-supplied.
