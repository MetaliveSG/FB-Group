---
description: Restore context after restart or compaction — read FB Group memory, recent rounds, current docker state, suggest files to review
user-invocable: true
---

You are resuming work on the **FB Group F&B CRM PoC** after a restart,
compaction, or context loss. Your goal is to rebuild working context FAST
so the user can pick up where they left off.

Run all independent steps in parallel where possible.

## Step 1: Read persistent memory (parallel)

Do ALL of these in parallel:

1. **Auto-memory index**: Read the MEMORY.md index at
   `/Users/samuelgan/.claude/projects/-Volumes-Data-Drive-Coding-multi-agent-FB-Group/memory/MEMORY.md`
   then read every file it references — at minimum:
   - `docs-index.md` (⭐ anti-hallucination map: which docs are AS-BUILT vs PLAN vs SUPERSEDED + ground-truth counts + clean-boot/real-credentials reality — trust this + code over stale doc prose)
   - `build-state.md` (the STATE file: pending work + the KIV backlog — no session narratives)
   - `project-fbgroup-crm.md` (scope, goals, demo loop)
   - `arch-decisions.md` (monorepo, polyglot, DB strategy, auth)
   - `user-prefs.md` (how the user wants me to operate)

1b. **Decision register**: Read `docs/decisions.md` — THE authority on what's currently
   decided (LOCKED/AGREED/DEFERRED/SUPERSEDED). At minimum the last ~12 rows; it outranks
   memory prose and doc narrative when they disagree.

1c. **Session history**: Read the TOP 2–3 dated entries of `docs/SESSION_NOTES.md` — the
   single session log (what changed, decisions, dense record, still-open). This replaces
   the old build-state "Round" narratives; deep history is in `build-state-archive` only.

2. **CLAUDE.md**: Read `/Volumes/Data Drive/Coding/multi_agent/FB Group/CLAUDE.md`
   for project conventions (if it exists).

3. **Delivery report**: Read `docs/delivery-report.md` for the consolidated
   current state — counts (endpoints/tables/migrations/tests/web routes),
   demo credentials, feature checklist, known limitations, roadmap.

4. **Git state**: This IS a git repo (origin `github.com/MetaliveSG/FB-Group`; **commit directly
   to `main`** — no PR flow, decision 2026-06-07; CI on push is informational). Run
   `git log --oneline -15`, `git status`, `git branch --show-current`, `git diff --stat`.
   "Save progress" = commit on `main` (+ memory for context not in code).

5. **Docker stack state**: Run `docker-compose -f infra/docker-compose.yml ps`
   and `curl -s http://localhost:8000/health` to see if the live stack is
   up. Note the api/web/db status.

6. **Pytest baseline**: Read `artifacts/pytest_results.txt` for the last
   passing test count — trust the artifact, not a hardcoded baseline here.

## Step 2: Synthesize context

From everything gathered, produce a **concise briefing** with these sections:

### Current State
- Counts (endpoints / tables / migrations / tests / web routes) — should match docs
- Docker stack: api/web/db healthy?
- Git: in a repo? clean working tree? uncommitted changes?
- Which modules were last touched (from the newest `docs/SESSION_NOTES.md` entry)

### Recent sessions (last 2-3)
- Summarise the top dated entries from `docs/SESSION_NOTES.md` — what shipped, what was verified live, what's KIV
- Highlight key decisions (cross-check `docs/decisions.md`) and any LESSON/GOTCHA lines from the Dense records

### Open Items & KIVs
- List every "**KIV**" entry in `build-state.md` (deferred work)
- List every "Queued next" / "Future" item
- Note any pending category/categorization issues, naming concerns flagged but unaddressed

### Suggested Reading
- Based on what was last touched, point to specific files worth re-reading
  (e.g. "Round 14 hardened `app/seed.py::_ensure_kampong_jackpot` — read before touching seed sync")
- Only suggest files that are recently modified or relevant to open items

### Demo Quick-Start (stack boots CLEAN — `SEED_ON_START=0`; seed first: `python -m app.seed_demo_merchants`)
- Operator login: `http://localhost:3001/platform/login` → `superadmin@platform.sg` / `Password123!`
- Merchant owner: `http://localhost:3001/merchant/login` → `owner@breadtalk.sg` / `owner@pepperlunch.sg` / `manager@toastbox.sg` — all `Password123!`
- Customer QR: scan a live Storefront's per-table QR (each Storefront's *Tables & QR* page) → OTP `+6580000000` (DEBUG returns the code). (Old static tokens like `orchard-01`/`kampong-bedok-01` are legacy `app/seed.py`-only — run `python -m app.seed_kampong` for the Kampong dataset.)

## Step 3: Ready prompt

End with:

```
Ready to continue. What would you like to work on?
```

## Rules

- Do NOT modify any files — this is read-only reconnaissance
- Keep the briefing under 80 lines — dense, no fluff
- If a file referenced in MEMORY.md doesn't exist, skip it and note it
- If docker-compose isn't running, say so — don't assume the stack is up
- This IS a git repo (direct-to-main, decision 2026-06-07); report branch + uncommitted changes in the briefing
- Prefer parallel tool calls to minimize latency
- Do NOT regenerate openapi.json or rerun pytest as part of catchup — that's a `/my-wrapup` action, not catchup

$ARGUMENTS
