"""RFM segmentation — Recency / Frequency / Monetary quintile scoring.

Scores each customer 1-5 on R, F, M (5 = best) using quintile ranking over the
merchant's customer base, then maps to a named segment (Champions, Loyal, At Risk…).
PoC: in-Python quintiles over the maintained loyalty-account metrics.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.enums import RewardScope
from app.models.identity import Customer
from app.models.loyalty import LoyaltyAccount


def _quintile(values: list[float], higher_is_better: bool = True) -> list[int]:
    n = len(values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: values[i])  # ascending by value
    scores = [0] * n
    for pos, idx in enumerate(order):
        scores[idx] = min(int(pos / n * 5), 4) + 1  # 1..5 ascending with value
    if not higher_is_better:
        scores = [6 - s for s in scores]
    return scores


def _segment(r: int, f: int, m: int) -> str:
    if r >= 4 and f >= 4:
        return "Champions"
    if f >= 4 and r >= 3:
        return "Loyal"
    if r >= 4 and f >= 2:
        return "Potential Loyalist"
    if r >= 4 and f <= 1:
        return "New Customers"
    if r <= 2 and m >= 4:
        return "Can't Lose Them"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Needs Attention"


def compute_rfm(db: Session, *, merchant_id: str, now: datetime | None = None) -> dict:
    now = now or utcnow()
    accounts = db.scalars(select(LoyaltyAccount).where(
        LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
        LoyaltyAccount.scope_id == merchant_id,
    )).all()
    if not accounts:
        return {"customers": [], "distribution": {}, "count": 0}

    recency = [((now - a.last_visit_at).days if a.last_visit_at else 9999) for a in accounts]
    frequency = [float(a.visit_count) for a in accounts]
    monetary = [float(a.total_spend or 0) for a in accounts]

    r_scores = _quintile(recency, higher_is_better=False)   # fewer days since visit = better
    f_scores = _quintile(frequency, higher_is_better=True)
    m_scores = _quintile(monetary, higher_is_better=True)

    customers = []
    distribution: dict[str, int] = {}
    for i, a in enumerate(accounts):
        cust = db.get(Customer, a.customer_id)
        seg = _segment(r_scores[i], f_scores[i], m_scores[i])
        distribution[seg] = distribution.get(seg, 0) + 1
        customers.append({
            "customer_id": a.customer_id,
            "name": cust.full_name if cust else a.customer_id,
            "recency_days": recency[i] if recency[i] < 9999 else None,
            "frequency": int(frequency[i]),
            "monetary": round(monetary[i], 2),
            "r": r_scores[i], "f": f_scores[i], "m": m_scores[i],
            "rfm": f"{r_scores[i]}{f_scores[i]}{m_scores[i]}",
            "segment": seg,
        })
    customers.sort(key=lambda c: (c["r"] + c["f"] + c["m"]), reverse=True)
    return {"customers": customers, "distribution": distribution, "count": len(customers)}
