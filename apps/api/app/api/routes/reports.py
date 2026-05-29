"""Sales reports + forecast routes (graph-ready). Outlet-permission respected."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import reports as rpt
from app.analytics import rfm as rfm_analytics
from app.auth.access import ALL_OUTLETS, Scope
from app.auth.deps import get_scope, require, resolve_merchant
from app.db.session import get_db
from app.schemas.insights import AIInsightsOut
from app.services import ai_insights as ai_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _allowed_outlets(scope: Scope, merchant_id: str, outlet_id: str | None):
    limit = scope.outlet_limit(merchant_id)
    base = None if limit is ALL_OUTLETS else set(limit)  # type: ignore[arg-type]
    if outlet_id:
        base = {outlet_id} if base is None else (base & {outlet_id})
    return base


def _ctx(scope: Scope, merchant_id: str | None, outlet_id: str | None):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "report.view", mid)
    return mid, _allowed_outlets(scope, mid, outlet_id)


@router.get("/summary")
def summary(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
            scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _ctx(scope, merchant_id, outlet_id)
    data = rpt.totals(db, merchant_id=mid, allowed_outlets=allowed)
    data.update(rpt.new_vs_repeat_revenue(db, merchant_id=mid, allowed_outlets=allowed))
    return data


@router.get("/sales")
def sales(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
          granularity: str = Query("day", pattern="^(day|week|month)$"),
          days: int = Query(90, ge=1, le=730),
          scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _ctx(scope, merchant_id, outlet_id)
    return rpt.sales_timeseries(db, merchant_id=mid, allowed_outlets=allowed, granularity=granularity, days=days)


@router.get("/top-items")
def top_items(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
              limit: int = Query(10, ge=1, le=50),
              scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _ctx(scope, merchant_id, outlet_id)
    return rpt.top_items(db, merchant_id=mid, allowed_outlets=allowed, limit=limit)


@router.get("/peak-hours")
def peak_hours(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
               scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _ctx(scope, merchant_id, outlet_id)
    return rpt.peak_hours(db, merchant_id=mid, allowed_outlets=allowed)


@router.get("/outlets")
def outlet_comparison(merchant_id: str | None = Query(None),
                      scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _ctx(scope, merchant_id, None)
    return rpt.outlet_comparison(db, merchant_id=mid, allowed_outlets=allowed)


@router.get("/forecast")
def forecast(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
             horizon: int = Query(7, ge=1, le=90), window: int = Query(7, ge=1, le=60),
             scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _ctx(scope, merchant_id, outlet_id)
    return rpt.forecast(db, merchant_id=mid, allowed_outlets=allowed, horizon_days=horizon, window=window)


@router.get("/rfm")
def rfm(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "report.view", mid)
    return rfm_analytics.compute_rfm(db, merchant_id=mid)


@router.get("/ai-insights", response_model=AIInsightsOut)
def ai_insights(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    """AI growth advisor — executive summary + ranked next-best actions over the
    merchant's analytics. Uses Claude when configured, else a deterministic heuristic."""
    mid, allowed = _ctx(scope, merchant_id, outlet_id)
    return ai_service.generate(db, merchant_id=mid, scope=scope, allowed_outlets=allowed)
