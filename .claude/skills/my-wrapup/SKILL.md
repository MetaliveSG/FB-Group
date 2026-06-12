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
- The new `docs/SESSION_NOTES.md` dated entry (THE single session log, incl. its Dense record line)
- The memory consolidation (Step 4): build-state backlog reconciliation, decisions to sweep into
  `docs/decisions.md`, lessons to promote, memories to mark superseded
- The git commit on `main` (it IS a repo; direct-to-main flow — see memory `workflow-direct-to-main`)
- Where the zip backup will be saved

**Wait for user confirmation before proceeding.**

## Step 1: Summarize session

Run `git diff HEAD` and `git status` (if a repo) OR review what was
discussed/changed in this session's working memory. Write a concise summary:
- What changed (features, fixes, refactors)
- Key decisions made and why
- Anything deferred to next session (KIV items)

## Step 1b: Update docs/SESSION_NOTES.md — THE session log (single log, decided 2026-06-12)

`docs/SESSION_NOTES.md` is the ONLY session journal (the old dual-log — a dense build-state "Round"
entry duplicating this — is retired; round narratives live in `build-state-archive`). Add a new dated
section at the **top** (newest-first):

```markdown
---

# Session — YYYY-MM-DD

## What changed
- Bullet list of changes, with file references

## Decisions
- Key decisions + the rationale (the "why") — each should already be a docs/decisions.md row

## Dense record
- Commits `<first>`…`<last>` · migrations: <names or none> · counts: <N endpoints · N tables ·
  N migrations · N+N tests · N routes> · verified: <one line of live-verification evidence>
- LESSON/GOTCHA one-liners worth keeping (these also get promoted in Step 4)

## Still open / next session
- Unfinished work, KIVs, follow-ups (mirror new KIVs into build-state's backlog, Step 4)
```

(**Proof of Work** discipline stands: for heavy/risky tasks — prod-like deploys, P0/P1 fixes,
migrations, security changes — save dated evidence under `artifacts/` as `YYYYMMDD_<desc>.{md,txt}`.)

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
- §12 verifier line: `N backend + N frontend tests pass` (use the live counts)
- §4 demo credentials block — keep current (breadtalk/pepperlunch/toastbox; clean-boot `SEED_ON_START=0`);
  also regenerate `artifacts/demo_credentials.md` if it drifted. New plan docs exist:
  `architecture-3-modules.md`, `buildplan-land-first.md`; keep the `docs-index` memory status tags current.

### docs/architecture/architecture.md
Verify and update:
- Overview line: `(N endpoints, N tables)` and `App Router, N routes`
- Frontend personas list — any new merchant page?
- Analytics / Services sections — new domain mention?

### docs/reference/api.md
Verify and update:
- New endpoint row(s) under the right section header — match `Method | Path | Notes` format
- If you added a new resource (e.g. `/me/jackpot`), confirm it's not duplicating elsewhere

### docs/reference/testing.md
Verify and update:
- Latest run line: `**N passed** across M files`
- Coverage section heading: `(N backend tests)`
- New row in the coverage table for each new test file

### docs/reference/database.md
Verify and update:
- Header: `**N migrations**` and `**N application tables**`
- Domain-grouped table list — add new tables to their domain row

### docs/reference/deployment.md
Verify and update:
- Migration chain narrative: `**N revisions** (initial → ... → newest)` and `verified to upgrade (N tables)`

### docs/reference/security.md
Update only if you added a new auth path, mock provider, or threat surface.

### docs/reference/bc-dr.md
Update only if recovery procedure or RPO/RTO changed.

### docs/reference/product-requirements.md
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

Run the full backend suite once more (baseline **287+**) and confirm green.
Run frontend (`cd apps/web && npm test`, baseline **58+** vitest). Pull the live counts from the run —
never hardcode a stale baseline.

## Step 4: Consolidate memory (MANDATORY — state · decisions · promote · expire)

The session NARRATIVE was already written once, in Step 1b (SESSION_NOTES — the single log).
This step maintains the STATE and distills the durable bits (the tiered-lifecycle decision,
2026-06-12 — memory `memory-lifecycle` + `docs/decisions.md`). Four sub-steps:

### 4a — Update the state file (build-state.md)
`~/.claude/.../memory/build-state.md` holds ONLY pending work + the KIV backlog (no session
narratives). Reconcile it: add KIVs raised this session, remove/strike items that shipped,
move PENDING items that completed. Keep entries to 1–3 lines with a pointer.

### 4b — Sweep firmed decisions into `docs/decisions.md`
Review the session for **major decisions the user firmed** ("locked", "agreed", "go with X",
overruled a design). Each should ALREADY have a row (the CLAUDE.md capture rule says append
in the same turn) — append any that were missed, and set Status `SUPERSEDED` on any row an
overruling decision replaced (never delete rows; fill the new row's *Supersedes* column).

### 4c — Promote
Any durable lesson/trap/how-to from this session that lives only in the SESSION_NOTES entry →
copy it to its semantic home: CLAUDE.md "Conventions & traps" for universal traps; the relevant
topic memory file otherwise (prefer absorbing into an existing file — see the no-drive-by rule;
if a new file is truly needed, add its MEMORY.md line in the same turn).

### 4d — Expire
Any memory file this session contradicted or superseded → update it or add
`status: superseded` to its frontmatter (+ note what replaced it). Don't delete.

## Step 5: Git commit + push (on `main`)

This IS a git repo (origin `github.com/MetaliveSG/FB-Group`); the workflow is **commit directly to
`main`** — no PR/branch (see memory `workflow-direct-to-main`; branch protection removed). Stage changed
files (NOT `.env`, `.venv`, `node_modules`, `pgdata`, `*.db`), commit:
```
session wrapup YYYY-MM-DD: <one-line summary>
```
End the message with the `Co-Authored-By: Claude …` trailer, then **`git push`**. CI runs on push
(informational / non-blocking — glance at it; fix-forward if it goes red).

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
- SESSION_NOTES.md dated entry added (the single session log)
- Consolidation done (build-state backlog reconciled · decisions swept into docs/decisions.md ·
  lessons promoted · superseded memories marked)
- Git: committed (hash) + pushed to main
- Backup: created at <path> (size) / skipped
- KIVs added this session
- Open items for next session

## Rules

- Read the top SESSION_NOTES entries before claiming what changed —
  many sessions touch the same files; the journal tells you what's actually new
- Never inflate counts to "round numbers" — pull the live counts from the
  artifacts you just regenerated
- Commit + push on `main` is the wrapup norm (direct-to-main flow); don't open a PR
- Never include `.env`, `.venv`, `node_modules`, `pgdata`, `*.db` in commits or backups
- If a doc update would be a cosmetic-only edit (no count or content shift),
  skip it — don't churn for churning
- If the test suite turns red, STOP. Surface the failure. Don't proceed
  to commit or backup over a broken state

$ARGUMENTS
