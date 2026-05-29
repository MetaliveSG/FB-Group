"""CRM analytics: per-customer metrics, lifecycle stage, churn risk, segments.

All values are derived on demand from the maintained loyalty account + transactions,
so the CRM never shows stale data. Thresholds are module constants (documented
PoC limitation: production would make these merchant-configurable).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.db.base import utcnow
from app.models.enums import LifecycleStage, LoyaltyTier
from app.models.identity import Customer
from app.models.loyalty import LoyaltyAccount

# --- Thresholds ---------------------------------------------------------
VIP_SPEND = 300.0
HIGH_SPENDER_SPEND = 200.0
FREQUENT_VISITS = 5
INACTIVE_DAYS = 60
AT_RISK_DAYS = 30
NEW_MAX_VISITS = 1
LOW_FREQ_MAX_VISITS = 2
DEFAULT_EXPECTED_INTERVAL_DAYS = 21.0


@dataclass
class CustomerMetrics:
    customer_id: str
    visit_count: int
    total_spend: float
    avg_spend: float
    points_balance: int
    lifetime_points: int
    tier: str
    first_visit_at: datetime | None
    last_visit_at: datetime | None
    days_since_last_visit: int | None
    visits_per_month: float
    churn_risk: float
    churn_label: str
    lifecycle_stage: str
    segments: list[str] = field(default_factory=list)


def _days_active(first: datetime | None, now: datetime) -> float:
    if not first:
        return 0.0
    return max((now - first).total_seconds() / 86400.0, 0.0)


def compute_metrics(account: LoyaltyAccount, customer: Customer, now: datetime | None = None) -> CustomerMetrics:
    now = now or utcnow()
    visits = account.visit_count
    total_spend = float(account.total_spend or 0)
    avg_spend = round(total_spend / visits, 2) if visits else 0.0

    days_since_last = int((now - account.last_visit_at).total_seconds() // 86400) if account.last_visit_at else None
    days_active = _days_active(account.first_visit_at, now)
    visits_per_month = round((visits / days_active) * 30.0, 2) if days_active >= 1 else float(visits)

    churn_risk, churn_label = _churn(visits, days_active, days_since_last)
    stage = _lifecycle(account, total_spend, days_since_last, visits)

    metrics = CustomerMetrics(
        customer_id=account.customer_id,
        visit_count=visits,
        total_spend=round(total_spend, 2),
        avg_spend=avg_spend,
        points_balance=account.points_balance,
        lifetime_points=account.lifetime_points,
        tier=account.tier,
        first_visit_at=account.first_visit_at,
        last_visit_at=account.last_visit_at,
        days_since_last_visit=days_since_last,
        visits_per_month=visits_per_month,
        churn_risk=churn_risk,
        churn_label=churn_label,
        lifecycle_stage=stage,
    )
    metrics.segments = compute_segments(metrics, customer, now)
    return metrics


def _churn(visits: int, days_active: float, days_since_last: int | None) -> tuple[float, str]:
    if days_since_last is None:
        return 0.0, "low"
    if visits >= 2 and days_active >= 1:
        avg_interval = max(days_active / (visits - 1), 1.0)
    else:
        avg_interval = DEFAULT_EXPECTED_INTERVAL_DAYS
    # 0 when fresh; ramps to 1.0 by ~3x the typical interval.
    risk = (days_since_last - avg_interval) / (avg_interval * 2.0)
    risk = round(min(1.0, max(0.0, risk)), 2)
    label = "high" if risk >= 0.66 else "medium" if risk >= 0.33 else "low"
    return risk, label


def _lifecycle(account: LoyaltyAccount, total_spend: float, days_since_last: int | None, visits: int) -> str:
    is_vip = account.tier in (LoyaltyTier.GOLD.value, LoyaltyTier.PLATINUM.value) or total_spend >= VIP_SPEND
    if days_since_last is not None and days_since_last > INACTIVE_DAYS:
        return LifecycleStage.DORMANT.value
    if is_vip:
        return LifecycleStage.VIP.value
    if visits <= NEW_MAX_VISITS:
        return LifecycleStage.NEW.value
    if days_since_last is not None and days_since_last > AT_RISK_DAYS:
        return LifecycleStage.AT_RISK.value
    return LifecycleStage.ACTIVE.value


# Standard segment keys exposed by the CRM (outlet_specific handled via filter).
STANDARD_SEGMENTS = [
    "vip", "inactive", "new", "frequent", "high_spender", "low_frequency", "birthday_month",
]


def compute_segments(m: CustomerMetrics, customer: Customer, now: datetime) -> list[str]:
    segs: list[str] = []
    if m.tier in (LoyaltyTier.GOLD.value, LoyaltyTier.PLATINUM.value) or m.total_spend >= VIP_SPEND:
        segs.append("vip")
    if m.days_since_last_visit is not None and m.days_since_last_visit > INACTIVE_DAYS:
        segs.append("inactive")
    if m.visit_count <= NEW_MAX_VISITS:
        segs.append("new")
    if m.visit_count >= FREQUENT_VISITS:
        segs.append("frequent")
    if m.total_spend >= HIGH_SPENDER_SPEND:
        segs.append("high_spender")
    if m.visit_count <= LOW_FREQ_MAX_VISITS and m.visit_count > NEW_MAX_VISITS:
        segs.append("low_frequency")
    if customer.birthday and customer.birthday.month == now.month:
        segs.append("birthday_month")
    return segs
