"""Promotions & retention campaign routes (staff campaign.manage)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.db.session import get_db
from app.models.campaigns import CampaignMessage
from app.schemas.campaigns import (
    AudienceResult,
    CampaignCreateIn,
    CampaignDetailOut,
    CampaignListItemOut,
    CampaignMetricsOut,
    CampaignOut,
    MessageOut,
    RedemptionIn,
    SendResultOut,
    VoucherIssueResult,
)
from app.services import campaigns as campaign_service
from app.services.audit import record as audit_record

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignListItemOut])
def list_campaigns(merchant_id: str | None = Query(default=None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    out = []
    for c in campaign_service.list_campaigns(db, merchant_id=mid):
        out.append(CampaignListItemOut(
            id=c.id, name=c.name, campaign_type=c.campaign_type, segment_key=c.segment_key,
            is_active=c.is_active, created_at=c.created_at,
            metrics=CampaignMetricsOut(**campaign_service.metrics(db, campaign=c)),
        ))
    return out


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(body: CampaignCreateIn, merchant_id: str | None = Query(default=None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    config = {"voucher": body.voucher.model_dump()} if body.voucher else None
    c = campaign_service.create_campaign(
        db, merchant_id=mid, name=body.name, campaign_type=body.campaign_type,
        segment_key=body.segment_key, message_template=body.message_template,
        reward_points=body.reward_points, starts_at=body.starts_at, ends_at=body.ends_at,
        scope_node_id=body.scope_node_id, config=config)
    audit_record(db, action="campaign.create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="campaign", entity_id=c.id)
    db.commit()
    db.refresh(c)
    return CampaignOut.model_validate(c)


@router.get("/{campaign_id}", response_model=CampaignDetailOut)
def campaign_detail(campaign_id: str, merchant_id: str | None = Query(default=None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    c = campaign_service.get_campaign(db, merchant_id=mid, campaign_id=campaign_id)
    msgs = db.scalars(
        select(CampaignMessage).where(CampaignMessage.campaign_id == c.id)
        .order_by(CampaignMessage.created_at.desc()).limit(50)
    ).all()
    return CampaignDetailOut(
        campaign=CampaignOut.model_validate(c),
        metrics=CampaignMetricsOut(**campaign_service.metrics(db, campaign=c)),
        messages=[MessageOut.model_validate(m) for m in msgs],
    )


@router.post("/{campaign_id}/audience", response_model=AudienceResult)
def build_audience(campaign_id: str, merchant_id: str | None = Query(default=None),
                   scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    c = campaign_service.get_campaign(db, merchant_id=mid, campaign_id=campaign_id)
    n = campaign_service.build_audience(db, merchant_id=mid, scope=scope, campaign=c)
    db.commit()
    return AudienceResult(audience_size=n)


@router.post("/{campaign_id}/issue-vouchers", response_model=VoucherIssueResult)
def issue_campaign_vouchers(campaign_id: str, merchant_id: str | None = Query(default=None),
                            scope=Depends(get_scope), db: Session = Depends(get_db)):
    """Issue the campaign's configured voucher to its audience (granted-voucher issuer)."""
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    c = campaign_service.get_campaign(db, merchant_id=mid, campaign_id=campaign_id)
    n = campaign_service.issue_campaign_vouchers(db, campaign=c)
    audit_record(db, action="campaign.issue_vouchers", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="campaign", entity_id=c.id, meta={"issued": n})
    db.commit()
    return VoucherIssueResult(issued=n)


@router.post("/{campaign_id}/send", response_model=SendResultOut)
def send_campaign(campaign_id: str, merchant_id: str | None = Query(default=None),
                  scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    c = campaign_service.get_campaign(db, merchant_id=mid, campaign_id=campaign_id)
    result = campaign_service.send_campaign(db, merchant_id=mid, campaign=c)
    audit_record(db, action="campaign.send", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="campaign", entity_id=c.id, meta=result)
    db.commit()
    return SendResultOut(**result)


@router.get("/{campaign_id}/metrics", response_model=CampaignMetricsOut)
def campaign_metrics(campaign_id: str, merchant_id: str | None = Query(default=None),
                     scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    c = campaign_service.get_campaign(db, merchant_id=mid, campaign_id=campaign_id)
    return CampaignMetricsOut(**campaign_service.metrics(db, campaign=c))


@router.post("/{campaign_id}/redemptions", status_code=201)
def record_redemption(campaign_id: str, body: RedemptionIn, merchant_id: str | None = Query(default=None),
                      scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    c = campaign_service.get_campaign(db, merchant_id=mid, campaign_id=campaign_id)
    campaign_service.record_redemption(db, merchant_id=mid, campaign=c, customer_id=body.customer_id,
                                       revenue=body.revenue, order_id=body.order_id)
    db.commit()
    return {"message": "redemption recorded"}
