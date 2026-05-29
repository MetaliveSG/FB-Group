---
description: End-of-session wrapup — summarize changes, verify docs alignment, regenerate artifacts, update memory, (optional) git commit, zip backup
user-invocable: true
---

You are closing out a work session on the **FB Group F&B CRM PoC**. Follow
these steps IN ORDER. **Before doing anything, print your full plan and
wait for the user to confirm.**

## Step 0: Plan (MUST DO FIRST)

Gather information silently, then print a numbered plan of exactly what
you will do. Include:
- Which files were changed this session (from `git diff` if a repo, or
  comparing against `~/.claude/.../memory/build-state.md`'s last Round entry)
- Which `docs/` files need updating (and what counts/lines)
- Whether artifacts need regenerating (`openapi.json`, `pytest_results.txt`, `schema_tables.txt`)
- What you'll write in `~/.claude/.../memory/build-state.md` (Round N entry)
- Whether to attempt a git commit (depends on whether repo is initialised)
- Where the zip backup will be saved

**Wait for user confirmation before proceeding.**

## Step 1: Summarize session

Run `git diff HEAD` and `git status` (if a repo) OR review what was
discussed/changed in this session's working memory. Write a concise summary:
- What changed (features, fixes, refactors)
- Key decisions made and why
- Anything deferred to next session (KIV items)

## Step 2: Regenerate artifacts (MANDATORY when counts may have shifted)

If any of these changed this session — endpoints / tables / migrations /
tests — regenerate the artifacts:

```bash
# OpenAPI spec + operation count
cd apps/api && .venv/bin/python - <<'PY'
import json
from app.main import app
from app.models import Base
spec = app.openapi()
ops = sum(1 for p, item in spec["paths"].items()
          for m in item if m in ("get","post","put","patch","delete"))
with open("../../artifacts/openapi.json", "w") as f:
    json.dump(spec, f, indent=2)
print(f"openapi: {len(spec['paths'])} paths · {ops} operations")
# Schema tables list
tables = sorted(Base.metadata.tables.keys())
with open("../../artifacts/schema_tables.txt", "w") as f:
    f.write("\n".join(tables) + "\n")
print(f"app tables: {len(tables)}")
PY

# pytest result
cd apps/api && .venv/bin/python -m pytest 2>&1 | tail -2
# Write the "N passed in Xs" line to artifacts/pytest_results.txt
```

Record the new counts. These drive Step 3.

## Step 3: Verify and update docs (MANDATORY)

This step is NOT optional. Always read and reconcile these files against
the current codebase state:

### docs/delivery-report.md (consolidated state — most important)
Verify and update:
- §2 line: `**N tables**, **N API endpoints**, N Alembic migrations`
- §2 frontend line: `**N routes**, typed API client`
- §2 extensions list — any new module / feature added this session?
- §5 feature checklist — new ✅ row if you added a major capability
- §6 test count: `**Backend: N passed** (pytest, M files)`
- §8 endpoints count in OpenAPI mention
- §9 heading: `Database schema (N tables)` + the domain narrative if a new domain was touched
- §10 known limitations — flag any new caveat
- §12 verifier line: `N backend + 37 frontend tests pass`

### docs/architecture.md
Verify and update:
- Overview line: `(N endpoints, N tables)` and `App Router, N routes`
- Frontend personas list — any new merchant page?
- Analytics / Services sections — new domain mention?

### docs/api.md
Verify and update:
- New endpoint row(s) under the right section header — match `Method | Path | Notes` format
- If you added a new resource (e.g. `/me/jackpot`), confirm it's not duplicating elsewhere

### docs/testing.md
Verify and update:
- Latest run line: `**N passed** across M files`
- Coverage section heading: `(N backend tests)`
- New row in the coverage table for each new test file

### docs/database.md
Verify and update:
- Header: `**N migrations**` and `**N application tables**`
- Domain-grouped table list — add new tables to their domain row

### docs/deployment.md
Verify and update:
- Migration chain narrative: `**N revisions** (initial → ... → newest)` and `verified to upgrade (N tables)`

### docs/security.md
Update only if you added a new auth path, mock provider, or threat surface.

### docs/bc-dr.md
Update only if recovery procedure or RPO/RTO changed.

### docs/product-requirements.md
Update only if scope or module list shifted materially.

For each file: if anything is stale, outdated, or missing — fix it.
Run the stale-count sweep when done:

```bash
grep -rnE "[0-9]+ (endpoint|table|migrat|revis|passed|backend|route)" docs/ *.md \
  | grep -vE "<current-correct-count>"
```

## Step 3b: Review test coverage for new features (MANDATORY)

Before declaring wrap, verify:

1. **Diff check**: Run `git diff --name-only` (or recall this session)
2. **New endpoints**: If any route was added/renamed/removed, verify there's a
   test in `apps/api/app/tests/test_*.py` covering it
3. **New models / migrations**: Verify the model is registered in `models/__init__.py`,
   migration runs cleanly on Postgres (`alembic upgrade head` succeeded in the API
   container), and a test exercises it
4. **New seed paths**: Verify the seed is idempotent (re-run reports `already_exists`
   or `inserted:0 / updated:0 / removed:0`) — see `_ensure_kampong_jackpot` as the
   reference idempotent-sync pattern
5. **New frontend pages**: Verify the page returns HTTP 200, the typed `@fbgroup/api-client`
   binding exists, and the merchant sidebar `ActiveKey` was extended if it's a
   merchant page
6. **Multi-tenant isolation**: For every new staff-facing endpoint, confirm a
   tenant-isolation test exists (or write one) via `/my-tester`

For each new/changed feature, ask:
- Happy path test? Negative test? Boundary test? Tenant isolation test?

Run the full backend suite once more (`90 baseline + new tests`) and confirm green.
Run frontend (`cd apps/web && npm test`, `37 baseline`).

## Step 4: Update memory (MANDATORY)

Append a new **Round N** entry to
`/Users/samuelgan/.claude/projects/-Volumes-Data-Drive-Coding-multi-agent-FB-Group/memory/build-state.md`
above the previous round. Format:

```markdown
**Round N (YYYY-MM-DD) — <one-line summary>.** <Concise but dense description of
what shipped: routes, services, models, migrations, seed changes, tests. Reference
specific files. Note any KIVs introduced. Note any architectural lesson worth
preserving (the "Lesson: ..." pattern from prior rounds). End with verification
evidence: "Live verified on Docker/Postgres: ..." with concrete numbers.>
```

If the session uncovered a recurring class of bug, also add a "**Bug fixed**" or
"**Gotcha**" entry — see the Round 14 entry on API-client-type-vs-backend-schema
drift for an example.

## Step 5: Git commit (CONDITIONAL)

Run `git rev-parse --is-inside-work-tree 2>&1`:
- **If a repo**: stage changed files (NOT `.env`, NOT `.venv`, NOT `node_modules`,
  NOT `pgdata`), commit with message:
  ```
  session wrapup YYYY-MM-DD: <one-line summary>
  ```
  Do NOT push unless explicitly asked.
- **If NOT a repo** (current state as of 2026-05-29): print a clear note that
  no commit was made because no git repo exists. Mention that the user previously
  declined / hadn't decided on `git init` — surface this as an open question if it
  hasn't been answered.

## Step 6: Zip backup (OPTIONAL — ask user)

Ask the user if they want a zip backup before doing it (large file, mostly
duplicates what's already on disk). If yes:

```bash
cd "/Volumes/Data Drive/Coding/multi_agent" && \
zip -r "FB_Group_backup_$(date +%Y-%m-%d_%H%M).zip" "FB Group" \
  -x "FB Group/.env" \
  -x "FB Group/apps/api/.venv/*" \
  -x "FB Group/apps/api/__pycache__/*" \
  -x "FB Group/apps/api/app/__pycache__/*" \
  -x "FB Group/apps/api/app/**/__pycache__/*" \
  -x "FB Group/apps/api/.pytest_cache/*" \
  -x "FB Group/apps/api/fbgroup.db" \
  -x "FB Group/apps/web/node_modules/*" \
  -x "FB Group/apps/web/.next/*" \
  -x "FB Group/packages/api-client/node_modules/*" \
  -x "FB Group/.git/*" \
  -x "FB Group/.DS_Store" \
  -x "*.pyc"
```

Print the zip path and file size when done.

## Step 7: Final report

Print a short summary:
- Files changed (count + list)
- Docs updated (which docs, what counts shifted)
- Artifacts regenerated (openapi paths/ops, schema_tables count, pytest result)
- Memory Round N appended
- Git: committed (hash) / no-repo (note) / skipped
- Backup: created at <path> (size) / skipped
- KIVs added this session
- Open items for next session

## Rules

- Read the build-state.md current state before claiming what changed —
  many sessions touch the same files, only the Round entry tells you what's new
- Never inflate counts to "round numbers" — pull the live counts from the
  artifacts you just regenerated
- Never push to remote unless explicitly asked
- Never include `.env`, `.venv`, `node_modules`, `pgdata`, `*.db` in commits or backups
- If a doc update would be a cosmetic-only edit (no count or content shift),
  skip it — don't churn for churning
- If the test suite turns red, STOP. Surface the failure. Don't proceed
  to commit or backup over a broken state

$ARGUMENTS
