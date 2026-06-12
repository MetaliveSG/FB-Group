# Reporting timezone — design & rules

_Split out of `CLAUDE.md` (2026-06-08) to keep per-turn guidance lean. The hard rule is summarised as a
trap in CLAUDE.md; this is the full rationale. Code: `app/analytics/timezones.py`,
`app/api/routes/reports.py::_tenant_tz`/`_scope`._

**ONE tz per report (default `Asia/Singapore`); Phase 1 done, DST-correct.** Timestamps are stored
naive-UTC (the canonical instant); reports localise **at read** via `app/analytics/timezones.py`:
- `to_local` = `zoneinfo`, DST-correct
- `local_day_bounds_utc` = inclusive local days → **HALF-OPEN** UTC bounds (`_txns` range is `[start, end)`)
- `valid_tz` / `require_tz` validate (strict → 422)

`tz` is threaded through bucketing (`sales`/`peak_hours`/`forecast`) + a per-request `?tz=`; default
`Asia/Singapore` → SG output unchanged. **The report tz is a SINGLE value for the whole report AND its
drill-down** — so parent total == Σ children and the date window is unambiguous.

**Phase 2 — BUILT (tenant-level tz + display dropdown).** `routes/reports.py::_tenant_tz` resolves the
ONE report tz: `explicit ?tz=` → `Merchant.settings["timezone"]` (the tenant's canonical reporting tz =
the "books"; settable in merchant Settings, strict-validated → 422 via `timezones.require_tz`) → platform
default. `_scope` returns it; `/reports/summary` echoes `timezone` so the UI labels it. The Reports page
has a **timezone dropdown** that defaults to the tenant tz (NOT the viewer's) and is a **display
override** — picking another shows a "differs from the business reporting timezone" banner (official
totals/payout/GST use the tenant tz).

**NEVER derive the report tz from `Outlet.timezone`** — a parent spans many outlets, so a per-outlet tz
makes `from`/`to` ambiguous and breaks parent↔child reconciliation. `Outlet.timezone` stays reserved for
a future opt-in single-outlet "in this store's local time" leaf view only.

**Phase 3 (deferred):** business-day start (e.g. 4am close, Square/Toast).
