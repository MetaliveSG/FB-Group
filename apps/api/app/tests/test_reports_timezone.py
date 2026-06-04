"""Report timezone helpers (multi-tz Phase 1). SG output is unchanged (UTC+8, no DST); the DST cases
prove why a FIXED offset is wrong and `zoneinfo` is required, and the day-bounds are half-open."""
from datetime import date, datetime

from app.analytics.timezones import (
    PLATFORM_DEFAULT_TZ,
    local_day_bounds_utc,
    to_local,
    valid_tz,
)


def test_to_local_sg_is_plus8():
    # 01:26 UTC → 09:26 SGT (matches the live data this replaced: order at 01:26 UTC = 09:26 SGT).
    assert to_local(datetime(2026, 6, 3, 1, 26), "Asia/Singapore") == datetime(2026, 6, 3, 9, 26)


def test_to_local_is_dst_aware():
    # New York: EDT (UTC-4) in summer, EST (UTC-5) in winter — a constant offset would be wrong.
    assert to_local(datetime(2026, 7, 1, 12, 0), "America/New_York").hour == 8   # EDT
    assert to_local(datetime(2026, 1, 1, 12, 0), "America/New_York").hour == 7   # EST


def test_local_day_bounds_sg_half_open():
    s, e = local_day_bounds_utc(date(2026, 6, 4), date(2026, 6, 4), "Asia/Singapore")
    assert s == datetime(2026, 6, 3, 16, 0)   # SG 06-04 00:00 = UTC 06-03 16:00
    assert e == datetime(2026, 6, 4, 16, 0)   # end EXCLUSIVE = SG 06-05 00:00 = UTC 06-04 16:00


def test_local_day_bounds_dst_spring_forward_is_23h():
    # US spring-forward (2026-03-08): the local day is 23h — a fixed -5h offset would make it 24h.
    s, e = local_day_bounds_utc(date(2026, 3, 8), date(2026, 3, 8), "America/New_York")
    assert (e - s).total_seconds() == 23 * 3600


def test_local_day_bounds_dst_fall_back_is_25h():
    # US fall-back (2026-11-01): the local day is 25h.
    s, e = local_day_bounds_utc(date(2026, 11, 1), date(2026, 11, 1), "America/New_York")
    assert (e - s).total_seconds() == 25 * 3600


def test_valid_tz_falls_back_on_garbage():
    assert valid_tz(None) == PLATFORM_DEFAULT_TZ
    assert valid_tz("Not/AZone") == PLATFORM_DEFAULT_TZ
    assert valid_tz("Asia/Kuala_Lumpur") == "Asia/Kuala_Lumpur"
