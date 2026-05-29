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
   - `build-state.md` (canonical: what's been built, every Round entry, every KIV)
   - `project-fbgroup-crm.md` (scope, goals, demo loop)
   - `arch-decisions.md` (monorepo, polyglot, DB strategy, auth)
   - `user-prefs.md` (how the user wants me to operate)

2. **CLAUDE.md**: Read `/Volumes/Data Drive/Coding/multi_agent/FB Group/CLAUDE.md`
   for project conventions (if it exists).

3. **Delivery report**: Read `docs/delivery-report.md` for the consolidated
   current state — counts (endpoints/tables/migrations/tests/web routes),
   demo credentials, feature checklist, known limitations, roadmap.

4. **Git state**: Run `git rev-parse --is-inside-work-tree` first. If
   it's a repo, run `git log --oneline -15`, `git status`, `git diff --stat`.
   If NOT a repo (currently the case — verified 2026-05-29), note that
   nothing is under version control; "save progress" means writing files
   to disk + memory, not commits.

5. **Docker stack state**: Run `docker-compose -f infra/docker-compose.yml ps`
   and `curl -s http://localhost:8000/health` to see if the live stack is
   up. Note the api/web/db status.

6. **Pytest baseline**: Read `artifacts/pytest_results.txt` for the last
   passing test count (current baseline: 90 backend + 37 frontend).

## Step 2: Synthesize context

From everything gathered, produce a **concise briefing** with these sections:

### Current State
- Counts (endpoints / tables / migrations / tests / web routes) — should match docs
- Docker stack: api/web/db healthy?
- Git: in a repo? clean working tree? uncommitted changes?
- Which modules were last touched (from the most recent Round in `build-state.md`)

### Recent Rounds (last 2-3)
- Summarise the most recent Round entries from `build-state.md` — what shipped, what was verified live, what's KIV
- Highlight key decisions and architectural lessons (e.g. round-12 SQLite-vs-Postgres VARCHAR overflow lesson, round-14 idempotent insert/update/remove sync pattern)

### Open Items & KIVs
- List every "**KIV**" entry in `build-state.md` (deferred work)
- List every "Queued next" / "Future" item
- Note any pending category/categorization issues, naming concerns flagged but unaddressed

### Suggested Reading
- Based on what was last touched, point to specific files worth re-reading
  (e.g. "Round 14 hardened `app/seed.py::_ensure_kampong_jackpot` — read before touching seed sync")
- Only suggest files that are recently modified or relevant to open items

### Demo Quick-Start
- Operator login: `http://localhost:3001/operator/login` → `superadmin@platform.sg` / `Password123!`
- Merchant owner: `http://localhost:3001/merchant/login` → `owner@makan.sg` (or `owner@kampongeats.sg`) / `Password123!`
- Customer QR: `http://localhost:3001/t/orchard-01` (or `kampong-bedok-01`) → OTP with `+6580000000` (or `+6581000000`)

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
- If `git` returns "not a git repository", note it explicitly (the user previously asked about commits — this is relevant)
- Prefer parallel tool calls to minimize latency
- Do NOT regenerate openapi.json or rerun pytest as part of catchup — that's a `/my-wrapup` action, not catchup

$ARGUMENTS
