"""Sales reporting + naive forecasting. Graph-ready (list-of-points) outputs.

Aggregation is done in Python from the transaction ledger so behaviour is identical
on SQLite and Postgres. PoC scale; production would push aggregation into SQL/warehouse.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.orders import OrderItem
from app.models.payments import Transaction
from app.models.tenancy import Outlet


def _txns(db: Session, merchant_id: str, allowed_outlets: set[str] | None,
          start: datetime | None = None, end: datetime | None = None) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.merchant_id == merchant_id)
    if allowed_outlets is not None:
        stmt = stmt.where(Transaction.outlet_id.in_(allowed_outlets))
    if start:
        stmt = stmt.where(Transaction.created_at >= start)
    if end:
        stmt = stmt.where(Transaction.created_at <= end)
    return list(db.scalars(stmt).all())


def _period_key(dt: datetime, granularity: str) -> str:
    if granularity == "month":
        return dt.strftime("%Y-%m")
    if granularity == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return dt.date().isoformat()


def sales_timeseries(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None,
                     granularity: str = "day", days: int = 90) -> list[dict]:
    now = utcnow()
    start = now - timedelta(days=days)
    txns = _txns(db, merchant_id, allowed_outlets, start=start)
    buckets: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
    for t in txns:
        key = _period_key(t.created_at, granularity)
        buckets[key]["revenue"] += float(t.amount)
        buckets[key]["orders"] += 1
    return [
        {"period": k, "revenue": round(v["revenue"], 2), "orders": v["orders"]}
        for k, v in sorted(buckets.items())
    ]


def totals(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None) -> dict:
    txns = _txns(db, merchant_id, allowed_outlets)
    revenue = round(sum(float(t.amount) for t in txns), 2)
    orders = len(txns)
    customers = len({t.customer_id for t in txns if t.customer_id})
    return {
        "revenue": revenue,
        "orders": orders,
        "unique_customers": customers,
        "avg_order_value": round(revenue / orders, 2) if orders else 0.0,
    }


def top_items(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None, limit: int = 10) -> list[dict]:
    paid_order_ids = [t.order_id for t in _txns(db, merchant_id, allowed_outlets)]
    if not paid_order_ids:
        return []
    rows = db.scalars(select(OrderItem).where(OrderItem.order_id.in_(paid_order_ids))).all()
    agg: dict[str, dict] = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    for r in rows:
        agg[r.name_snapshot]["quantity"] += r.quantity
        agg[r.name_snapshot]["revenue"] += float(r.line_total)
    items = [{"name": k, "quantity": v["quantity"], "revenue": round(v["revenue"], 2)} for k, v in agg.items()]
    items.sort(key=lambda x: x["revenue"], reverse=True)
    return items[:limit]


def peak_hours(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None) -> list[dict]:
    txns = _txns(db, merchant_id, allowed_outlets)
    buckets: dict[int, dict] = {h: {"orders": 0, "revenue": 0.0} for h in range(24)}
    for t in txns:
        h = t.created_at.hour
        buckets[h]["orders"] += 1
        buckets[h]["revenue"] += float(t.amount)
    return [{"hour": h, "orders": v["orders"], "revenue": round(v["revenue"], 2)} for h, v in buckets.items()]


def outlet_comparison(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None) -> list[dict]:
    txns = _txns(db, merchant_id, allowed_outlets)
    agg: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "orders": 0})
    for t in txns:
        agg[t.outlet_id]["revenue"] += float(t.amount)
        agg[t.outlet_id]["orders"] += 1
    out = []
    for outlet_id, v in agg.items():
        outlet = db.get(Outlet, outlet_id)
        out.append({
            "outlet_id": outlet_id,
            "outlet_name": outlet.name if outlet else outlet_id,
            "revenue": round(v["revenue"], 2),
            "orders": v["orders"],
        })
    out.sort(key=lambda x: x["revenue"], reverse=True)
    return out


def new_vs_repeat_revenue(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None) -> dict:
    """First transaction per customer counts as 'new' revenue; the rest 'repeat'."""
    txns = sorted(_txns(db, merchant_id, allowed_outlets), key=lambda t: t.created_at)
    seen: set[str] = set()
    new_rev = repeat_rev = 0.0
    for t in txns:
        if not t.customer_id:
            new_rev += float(t.amount)
            continue
        if t.customer_id in seen:
            repeat_rev += float(t.amount)
        else:
            seen.add(t.customer_id)
            new_rev += float(t.amount)
    return {"new_customer_revenue": round(new_rev, 2), "repeat_customer_revenue": round(repeat_rev, 2)}


def forecast(db: Session, *, merchant_id: str, allowed_outlets: set[str] | None,
             horizon_days: int = 7, window: int = 7) -> dict:
    """Naive moving-average forecast.

    LIMITATIONS (PoC): flat moving average of the trailing `window` days. Ignores
    seasonality, weekday effects, promotions, and trend. Production would use a
    proper time-series model (Prophet/ARIMA/ETS) trained per outlet.
    """
    now = utcnow()
    daily = sales_timeseries(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets,
                             granularity="day", days=max(window * 3, 30))
    by_day = {d["period"]: d["revenue"] for d in daily}

    # Build a continuous trailing window ending today (fill gaps with 0).
    trailing = []
    for i in range(window, 0, -1):
        day = (now.date() - timedelta(days=i)).isoformat()
        trailing.append(by_day.get(day, 0.0))
    avg = round(sum(trailing) / window, 2) if window else 0.0

    points = []
    for i in range(1, horizon_days + 1):
        d = (now.date() + timedelta(days=i)).isoformat()
        points.append({"date": d, "projected_revenue": avg})

    return {
        "method": "moving_average",
        "window_days": window,
        "horizon_days": horizon_days,
        "moving_average": avg,
        "history": daily[-window:],
        "forecast": points,
        "limitations": "Flat MA; no seasonality/trend/weekday effects. PoC only.",
    }
