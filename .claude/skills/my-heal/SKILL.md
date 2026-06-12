---
description: Self-heal the persistent memory estate — audit every .md (CLAUDE.md, docs/, memory dir, skills) against code reality, fix stale claims/counts/paths autonomously, merge bloat, expire superseded; report what was healed. Run when things feel stale or after a big stretch.
user-invocable: true
---

You are running a **memory-heal pass** on the FB Group/CIP project: verify the persistent-memory
estate against reality, fix drift autonomously, and report. The goal is that every always-read file
is TRUE, REGISTERED, and as SMALL as it can be. (This codifies the 2026-06-12 manual audit that found
stale demo tokens, "PLAN" headers on built features, and skills contradicting locked decisions.)

**Scope:** `CLAUDE.md` · `docs/**` · the memory dir
(`~/.claude/projects/-Volumes-Data-Drive-Coding-multi-agent-FB-Group/memory/`) · `.claude/skills/*/SKILL.md`.

## Phase 1 — Ground truth (gather BEFORE judging; parallel)
- Live counts: regenerate or read `artifacts/` (openapi ops, schema tables, pytest/vitest counts,
  `ls apps/web/src/app/**/page.tsx | wc -l`, `ls apps/api/alembic/versions | wc -l`).
- `git log --oneline -20` (what actually shipped recently) + `docs/decisions.md` (what's decided).
- Docker/seed reality: which seeds exist (`ls apps/api/app/seed*`), demo creds from the seed source.

## Phase 2 — Audit (find drift; report each finding as file:line → claim → reality)
1. **Stale counts:** grep every count claim (`[0-9]+ (endpoint|table|migrat|test|route)`) in
   CLAUDE.md, docs/, memory dir → compare to Phase-1 truth.
2. **Broken pointers:** every `docs/...` path mentioned anywhere must exist on disk; every
   `[[wikilink]]` in the memory dir must match an existing memory `name:`; every skill's file
   references must exist.
3. **Status-tag drift:** docs whose header says PLAN but git/decisions say BUILT (and vice versa);
   `docs/README.md` rows vs each doc's own header; the `docs-index` memory vs both.
4. **Contradiction scan:** for the ~10 newest `docs/decisions.md` rows, grep for prose still
   asserting the SUPERSEDED framing (the killer class — old framings poison generation).
5. **Registration check:** every `docs/**.md` has a README row; every memory file has a MEMORY.md
   line; flag orphans of both kinds (file w/o index line, index line w/o file).
6. **Bloat check:** CLAUDE.md ≤ ~2,300 words; memory files > ~800 words or two files sharing a
   domain → merge candidates (one-file-per-domain rule, memory `user-prefs`).
7. **Staleness probe:** any memory file untouched >30 days that makes claims about code — spot-check
   ONE claim each against the code; flag the file if it fails.

## Phase 3 — Heal (apply autonomously; keep the diff reviewable)
- **Fix mechanically, no confirmation needed:** wrong counts, broken paths, missing registrations,
  README/status-tag mismatches where git history is unambiguous, superseded prose (rewrite to the
  decided model + pointer).
- **Mark, don't delete:** contradicted memories get `status: superseded` frontmatter + what replaced
  them; decisions.md rows are NEVER deleted.
- **Propose, don't apply** (list for the user): domain merges of substantive files, deleting
  anything, status changes where reality is ambiguous.
- Respect the standing rules: no new .md files (heal SHRINKS the estate); same-turn registration for
  anything touched; CLAUDE.md stays constitution-only.

## Phase 4 — Report + commit
- Print: findings count by class · what was auto-healed (file → one-line fix) · proposed merges/
  deletions awaiting the user · estate size trend (memory file count + CLAUDE.md words + always-read
  token estimate vs last heal — append one line to the "Heal log" at the bottom of memory
  `memory-lifecycle.md` so the trend is visible).
- Commit repo-side fixes directly to `main`: `chore(heal): memory-heal pass YYYY-MM-DD — <n> fixes`.
- If the pass found ZERO drift, say so and stop — do not churn files to look busy.

## Rules
- Truth order: code > artifacts > decisions.md > docs > memory prose.
- Read before fixing — never rewrite a claim you haven't verified against Phase-1 truth.
- Small, surgical diffs; if a fix balloons, downgrade it to a proposal.
- This skill must leave the estate SMALLER or equal, never larger.

$ARGUMENTS
