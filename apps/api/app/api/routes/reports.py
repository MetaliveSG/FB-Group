"""Sales reports + forecast routes (graph-ready), node-scoped + RBAC-enforced.

SCOPE (the SOURCE selector): a platform operator may report on the whole ecosystem ("Platform",
all merchants) or any node; a node account is confined to its own node + downline — never upline,
siblings, or another tenant (enforced server-side, not just hidden in the UI). Resolution:
`?node_id=` → that node's subtree; `?platform=true` (operators only) → all merchants.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import reports as rpt
from app.analytics import rfm as rfm_analytics
from app.analytics.timezones import local_day_bounds_utc, valid_tz
from app.auth.access import ALL_OUTLETS, Scope
from app.auth.deps import get_scope, require, resolve_merchant
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.catalog import Menu
from app.models.org import OrgNode
from app.schemas.insights import AIInsightsOut
from app.services import ai_insights as ai_service
from app.services import org_tree

router = APIRouter(prefix="/reports", tags=["reports"])


# ── scope ──────────────────────────────────────────────────────────────────
def _is_operator(scope: Scope) -> bool:
    return (getattr(scope, "is_super_admin", False)
            or getattr(scope, "platform_drilldown", None) is not None
            or "platform.merchants.view" in getattr(scope, "platform_perms", set()))


def _subtree_outlet_ids(db: Session, node: OrgNode) -> set[str]:
    """Typed Outlet ids under a node — its sellable storefronts (menu.id == node.id → outlet)."""
    menu_node_ids = {n.id for n in org_tree.sellable_under(db, node, active_only=False)}
    if not menu_node_ids:
        return set()
    return set(db.scalars(select(Menu.outlet_id).where(Menu.id.in_(menu_node_ids))).all())


def _legacy_allowed(scope: Scope, merchant_id: str, outlet_id: str | None):
    limit = scope.outlet_limit(merchant_id)
    base = None if limit is ALL_OUTLETS else set(limit)  # type: ignore[arg-type]
    if outlet_id:
        base = {outlet_id} if base is None else (base & {outlet_id})
    return base


def _scope(db: Session, scope: Scope, node_id: str | None, platform: bool,
           merchant_id: str | None, outlet_id: str | None):
    """Resolve the report scope → (merchant_id|None, allowed_outlets|None) + enforce RBAC.
    Platform (operators only) → (None, None) = every merchant. A node → its subtree outlets, only if
    the caller can SEE that node (operators see all; a node account sees its node + downline only)."""
    if platform:
        if not _is_operator(scope):
            raise ForbiddenError("Platform report requires an operator", code="forbidden")
        return None, None
    if node_id:
        node = org_tree.node_for(db, node_id)
        if node is None:
            raise NotFoundError("Node not found", code="node_not_found")
        if not _is_operator(scope):
            visible = {n.id for n in org_tree.visible_nodes(db, scope)}
            if node.id not in visible:                       # upline / sibling / foreign → blocked
                raise ForbiddenError("Outside your scope", code="forbidden")
            # report.view on the tenant(s) this node covers (a group node spans several boundaries).
            boundaries = {n.settlement_account_id for n in org_tree.subtree(db, node, active_only=False)
                          if n.is_settlement_boundary} or {node.settlement_account_id}
            if not all(scope.can("report.view", m) for m in boundaries):
                raise ForbiddenError("Missing permission: report.view", code="forbidden")
        # merchant_id=None → filter purely by the subtree's outlets (correct even when a group node
        # spans multiple tenant merchants); the outlet set already confines the scope.
        return None, _subtree_outlet_ids(db, node)
    # No node + no platform: operator defaults to Platform; everyone else to their merchant scope.
    if _is_operator(scope):
        return None, None
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "report.view", mid)
    return mid, _legacy_allowed(scope, mid, outlet_id)


def _range(start: str | None, end: str | None, tz: str):
    """Parse YYYY-MM-DD as report-tz-local calendar days → HALF-OPEN naive-UTC bounds [start, end_excl)
    for the naive-UTC ledger. DST-correct (zoneinfo). Both ends are needed together; if only one is
    given the other defaults to it (a single-day range)."""
    if not start and not end:
        return None, None
    d_from = date.fromisoformat(start) if start else date.fromisoformat(end)  # type: ignore[arg-type]
    d_to = date.fromisoformat(end) if end else date.fromisoformat(start)      # type: ignore[arg-type]
    return local_day_bounds_utc(d_from, d_to, tz)


# ── endpoints ────────────────────────────────────────────────────────────────
@router.get("/summary")
def summary(node_id: str | None = Query(None), platform: bool = Query(False),
            merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
            start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
            scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    s, e = _range(start, end, valid_tz(tz))
    data = rpt.totals(db, merchant_id=mid, allowed_outlets=allowed, start=s, end=e)
    data.update(rpt.new_vs_repeat_revenue(db, merchant_id=mid, allowed_outlets=allowed, start=s, end=e))
    return data


@router.get("/sales")
def sales(node_id: str | None = Query(None), platform: bool = Query(False),
          merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
          granularity: str = Query("day", pattern="^(hour|day|week|month)$"),
          days: int = Query(90, ge=1, le=730),
          start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
          scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    rtz = valid_tz(tz)
    s, e = _range(start, end, rtz)
    return rpt.sales_timeseries(db, merchant_id=mid, allowed_outlets=allowed,
                                granularity=granularity, days=days, start=s, end=e, tz=rtz)


@router.get("/top-items")
def top_items(node_id: str | None = Query(None), platform: bool = Query(False),
              merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
              limit: int = Query(10, ge=1, le=50),
              start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
              scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    s, e = _range(start, end, valid_tz(tz))
    return rpt.top_items(db, merchant_id=mid, allowed_outlets=allowed, limit=limit, start=s, end=e)


@router.get("/peak-hours")
def peak_hours(node_id: str | None = Query(None), platform: bool = Query(False),
               merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
               start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
               scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    rtz = valid_tz(tz)
    s, e = _range(start, end, rtz)
    return rpt.peak_hours(db, merchant_id=mid, allowed_outlets=allowed, start=s, end=e, tz=rtz)


@router.get("/payments")
def payments(node_id: str | None = Query(None), platform: bool = Query(False),
             merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
             start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
             scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    s, e = _range(start, end, valid_tz(tz))
    return rpt.payment_split(db, merchant_id=mid, allowed_outlets=allowed, start=s, end=e)


@router.get("/outlets")
def outlet_comparison(node_id: str | None = Query(None), platform: bool = Query(False),
                      merchant_id: str | None = Query(None),
                      start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
                      scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, None)
    s, e = _range(start, end, valid_tz(tz))
    return rpt.outlet_comparison(db, merchant_id=mid, allowed_outlets=allowed, start=s, end=e)


@router.get("/rollup")
def rollup(node_id: str | None = Query(None), platform: bool = Query(False),
           start: str | None = Query(None), end: str | None = Query(None), tz: str | None = Query(None),
           scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Per-CHILD breakdown for the member-tree drill-down: Platform → each tenant; a node → its
    direct children (each child's whole-subtree totals). Same RBAC as the other reports."""
    _scope(db, scope, node_id, platform, None, None)   # enforce visibility/perms for this node
    s, e = _range(start, end, valid_tz(tz))
    if platform or (node_id is None and _is_operator(scope)):
        children = list(db.scalars(select(OrgNode).where(OrgNode.depth == 0).order_by(OrgNode.name)).all())
    else:
        parent = org_tree.node_for(db, node_id)
        children = list(db.scalars(
            select(OrgNode).where(OrgNode.parent_id == node_id).order_by(OrgNode.name)).all()
        ) if parent else []
    rows = []
    for c in children:
        outs = _subtree_outlet_ids(db, c)
        t = rpt.totals(db, merchant_id=None, allowed_outlets=outs, start=s, end=e)
        rows.append({"node_id": c.id, "name": c.name or c.id, "role": c.role, "sells": c.sells,
                     "revenue": t["revenue"], "orders": t["orders"], "avg_order_value": t["avg_order_value"]})
    rows.sort(key=lambda r: r["revenue"], reverse=True)
    return rows


@router.get("/forecast")
def forecast(node_id: str | None = Query(None), platform: bool = Query(False),
             merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
             horizon: int = Query(7, ge=1, le=90), window: int = Query(7, ge=1, le=60),
             tz: str | None = Query(None),
             scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    return rpt.forecast(db, merchant_id=mid, allowed_outlets=allowed, horizon_days=horizon,
                        window=window, tz=valid_tz(tz))


@router.get("/rfm")
def rfm(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "report.view", mid)
    return rfm_analytics.compute_rfm(db, merchant_id=mid)


@router.get("/ai-insights", response_model=AIInsightsOut)
def ai_insights(merchant_id: str | None = Query(None), outlet_id: str | None = Query(None),
                node_id: str | None = Query(None), platform: bool = Query(False),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    """AI growth advisor — executive summary + ranked next-best actions. Uses Claude when
    configured, else a deterministic heuristic. Scoped like the other reports."""
    mid, allowed = _scope(db, scope, node_id, platform, merchant_id, outlet_id)
    if mid is None:   # Platform aggregate has no single merchant; insights are per-merchant
        raise ForbiddenError("Pick a merchant/node for AI insights", code="needs_merchant")
    return ai_service.generate(db, merchant_id=mid, scope=scope, allowed_outlets=allowed)
