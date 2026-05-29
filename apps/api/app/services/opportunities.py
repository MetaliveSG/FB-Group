"""Opportunities + pipeline. Supports configurable pipeline modes:
- "sales"   : prospecting → qualified → proposal → negotiation → won/lost
- "winback" : at_risk → contacted → offer_sent → recovered/churned
Each mode has its own ordered stage set (PIPELINE_DEFS)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.money import money
from app.db.base import utcnow
from app.models.engagement import Opportunity
from app.models.enums import PIPELINE_DEFS


def _pdef(pipeline_type: str) -> dict:
    d = PIPELINE_DEFS.get(pipeline_type)
    if not d:
        raise AppError(f"Unknown pipeline type '{pipeline_type}'", code="bad_pipeline_type", status_code=400)
    return d


def create_opportunity(
    db: Session, *, merchant_id: str, customer_id: str, name: str,
    amount: Decimal | float = 0, pipeline_type: str = "sales", stage: str | None = None,
    expected_close_date: date | None = None, owner_user_id: str | None = None,
    created_by_user_id: str | None = None,
) -> Opportunity:
    d = _pdef(pipeline_type)
    stage = stage or d["open"][0]
    if stage not in d["stages"]:
        raise ConflictError(f"Stage '{stage}' not valid for {pipeline_type} pipeline", code="bad_stage")
    opp = Opportunity(
        merchant_id=merchant_id, customer_id=customer_id, name=name, pipeline_type=pipeline_type,
        amount=money(amount), stage=stage, expected_close_date=expected_close_date,
        owner_user_id=owner_user_id, created_by_user_id=created_by_user_id,
    )
    if stage in (d["won"], d["lost"]):
        opp.closed_at = utcnow()
    db.add(opp)
    db.flush()
    return opp


def list_opportunities(db: Session, *, merchant_id: str, pipeline_type: str | None = None) -> list[Opportunity]:
    stmt = select(Opportunity).where(Opportunity.merchant_id == merchant_id)
    if pipeline_type:
        stmt = stmt.where(Opportunity.pipeline_type == pipeline_type)
    return list(db.scalars(stmt.order_by(Opportunity.created_at.desc())).all())


def list_for_customer(db: Session, *, merchant_id: str, customer_id: str) -> list[Opportunity]:
    return list(db.scalars(
        select(Opportunity).where(
            Opportunity.merchant_id == merchant_id, Opportunity.customer_id == customer_id
        ).order_by(Opportunity.created_at.desc())
    ).all())


def update_opportunity(db: Session, *, merchant_id: str, opp_id: str,
                       stage: str | None = None, amount: Decimal | float | None = None) -> Opportunity:
    opp = db.get(Opportunity, opp_id)
    if not opp or opp.merchant_id != merchant_id:
        raise NotFoundError("Opportunity not found", code="opportunity_not_found")
    if stage is not None:
        d = _pdef(opp.pipeline_type)
        if stage not in d["stages"]:
            raise ConflictError(f"Stage '{stage}' not valid for {opp.pipeline_type} pipeline", code="bad_stage")
        opp.stage = stage
        opp.closed_at = utcnow() if stage in (d["won"], d["lost"]) else None
    if amount is not None:
        opp.amount = money(amount)
    db.flush()
    return opp


def pipeline(db: Session, *, merchant_id: str, pipeline_type: str = "sales") -> dict:
    d = _pdef(pipeline_type)
    rows = db.execute(
        select(Opportunity.stage, func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0))
        .where(Opportunity.merchant_id == merchant_id, Opportunity.pipeline_type == pipeline_type)
        .group_by(Opportunity.stage)
    ).all()
    by_stage = {stage: {"count": int(c), "value": round(float(v), 2)} for stage, c, v in rows}
    stages = []
    for s in d["stages"]:
        cell = by_stage.get(s, {"count": 0, "value": 0.0})
        stages.append({"stage": s, "count": cell["count"], "value": cell["value"],
                       "is_open": s in d["open"], "is_won": s == d["won"], "is_lost": s == d["lost"]})
    return {
        "pipeline_type": pipeline_type,
        "stages": stages,
        "open_value": round(sum(x["value"] for x in stages if x["is_open"]), 2),
        "won_value": next((x["value"] for x in stages if x["is_won"]), 0.0),
        "open_count": sum(x["count"] for x in stages if x["is_open"]),
    }
