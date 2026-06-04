"""Timezone helpers for reporting (Phase 1 of multi-timezone).

Storage is naive-UTC (`app.db.base.utcnow`) — one canonical instant. *Presentation* (which day/hour a
sale falls in, and the date-range boundaries) depends on the report's timezone, resolved per request.
DST-correct via `zoneinfo` (NOT a fixed offset — a constant offset is wrong for any DST zone).

Phase 1: helpers + a `tz` parameter threaded through reports, defaulting to SG (output identical to the
old fixed +8h). Phase 2 (deferred) wires the source: per-outlet `Outlet.timezone` for a single-outlet
report, and a tenant default for cross-outlet/group rollups. See CLAUDE.md + docs/architecture-org-tree.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PLATFORM_DEFAULT_TZ = "Asia/Singapore"


def valid_tz(tz: str | None) -> str:
    """Return `tz` if it's a real IANA zone, else the platform default (a bad string would 500 at read)."""
    if not tz:
        return PLATFORM_DEFAULT_TZ
    try:
        ZoneInfo(tz)
        return tz
    except (ZoneInfoNotFoundError, ValueError):
        return PLATFORM_DEFAULT_TZ


def require_tz(tz: str) -> str:
    """Strict: return `tz` if it's a real IANA zone, else raise ValueError — for WRITE-time validation
    (a bad reporting timezone should 422 on save, not silently fall back). `valid_tz` is the read path."""
    try:
        ZoneInfo(tz)
        return tz
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone: {tz!r}") from exc


def to_local(dt_utc_naive: datetime, tz: str) -> datetime:
    """Naive-UTC instant → naive local wall-clock (for day/hour bucketing keys). DST-correct."""
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz)).replace(tzinfo=None)


def local_day_bounds_utc(d_from: date, d_to: date, tz: str) -> tuple[datetime, datetime]:
    """Inclusive local-date range [d_from, d_to] → HALF-OPEN naive-UTC bounds [start, end_exclusive).

    end is the start of the day AFTER d_to, so the query is `created_at >= start AND created_at < end`
    — no microsecond gap, no double-count. zoneinfo applies the offset valid on each date, so a DST
    spring-forward (23h) or fall-back (25h) day is exact."""
    z = ZoneInfo(tz)
    start = datetime.combine(d_from, time.min, tzinfo=z)
    end_excl = datetime.combine(d_to + timedelta(days=1), time.min, tzinfo=z)
    return (start.astimezone(timezone.utc).replace(tzinfo=None),
            end_excl.astimezone(timezone.utc).replace(tzinfo=None))
