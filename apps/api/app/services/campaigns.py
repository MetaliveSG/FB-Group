"""Promotions & retention campaigns: audience by segment, mock WhatsApp send,
redemption + performance tracking (sent/delivered/redeemed/revenue/conversion/ROI)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.access import Scope
from app.core.errors import ConflictError, NotFoundError
from app.core.money import money
from app.models.campaigns import Campaign, CampaignAudience, CampaignMessage, CampaignRedemption
from app.models.enums import CampaignType, MessageStatus
from app.models.identity import Customer
from app.services import crm as crm_service
from app.services import whatsapp

# WhatsApp message cost (SGD) used for a simple ROI calc.
MSG_COST = 0.02

# Default target segment per campaign type (overridable via campaign.segment_key).
DEFAULT_SEGMENT = {
    CampaignType.BIRTHDAY.value: "birthday_month",
    CampaignType.WINBACK.value: "inactive",
    CampaignType.NEW_CUSTOMER_RETURN.value: "new",
    CampaignType.VIP_REWARD.value: "vip",
    CampaignType.WEEKDAY_BOOST.value: "frequent",
    CampaignType.WHATSAPP_PROMO.value: None,  # all customers unless segment_key set
}


def create_campaign(db: Session, *, merchant_id: str, name: str, campaign_type: str,
                    segment_key: str | None = None, message_template: str = "",
                    reward_points: int = 0, starts_at: datetime | None = None,
                    ends_at: datetime | None = None, config: dict | None = None) -> Campaign:
    campaign = Campaign(
        merchant_id=merchant_id, name=name, campaign_type=campaign_type,
        segment_key=segment_key, message_template=message_template, reward_points=reward_points,
        starts_at=starts_at, ends_at=ends_at, config=config or {},
    )
    db.add(campaign)
    db.flush()
    return campaign


def get_campaign(db: Session, *, merchant_id: str, campaign_id: str) -> Campaign:
    c = db.get(Campaign, campaign_id)
    if not c or c.merchant_id != merchant_id:
        raise NotFoundError("Campaign not found", code="campaign_not_found")
    return c


def list_campaigns(db: Session, *, merchant_id: str) -> list[Campaign]:
    return list(db.scalars(
        select(Campaign).where(Campaign.merchant_id == merchant_id).order_by(Campaign.created_at.desc())
    ).all())


def _target_segment(campaign: Campaign) -> str | None:
    if campaign.segment_key:
        return campaign.segment_key
    return DEFAULT_SEGMENT.get(campaign.campaign_type)


def build_audience(db: Session, *, merchant_id: str, scope: Scope, campaign: Campaign) -> int:
    segment = _target_segment(campaign)
    items = crm_service.list_customers(db, merchant_id=merchant_id, scope=scope, segment=segment)
    db.query(CampaignAudience).filter(CampaignAudience.campaign_id == campaign.id).delete()
    for it in items:
        db.add(CampaignAudience(campaign_id=campaign.id, customer_id=it.customer.id))
    db.flush()
    return len(items)


def _render(template: str, customer: Customer) -> str:
    name = (customer.full_name or "there").split()[0]
    return (template or "Hi {name}, we have an offer for you!").replace("{name}", name)


def send_campaign(db: Session, *, merchant_id: str, campaign: Campaign,
                  provider: whatsapp.MockWhatsAppProvider | None = None) -> dict:
    provider = provider or whatsapp.get_provider()
    audience = db.scalars(
        select(CampaignAudience).where(CampaignAudience.campaign_id == campaign.id)
    ).all()
    if not audience:
        raise ConflictError("Build the audience before sending", code="empty_audience")

    already = set(db.scalars(
        select(CampaignMessage.customer_id).where(CampaignMessage.campaign_id == campaign.id)
    ).all())

    delivered = failed = 0
    for a in audience:
        if a.customer_id in already:
            continue
        customer = db.get(Customer, a.customer_id)
        if not customer:
            continue
        body = _render(campaign.message_template, customer)
        result = whatsapp.send_with_retry(provider, to=customer.phone or "", body=body)
        db.add(CampaignMessage(
            campaign_id=campaign.id, customer_id=customer.id, channel="whatsapp",
            to_address=customer.phone or "", body=body, status=result.status,
            provider_ref=result.provider_ref, attempts=result.attempts,
        ))
        if result.status == MessageStatus.DELIVERED.value:
            delivered += 1
        else:
            failed += 1
    db.flush()
    return {"delivered": delivered, "failed": failed, "audience": len(audience)}


def record_redemption(db: Session, *, merchant_id: str, campaign: Campaign, customer_id: str,
                      revenue: Decimal | float = 0, order_id: str | None = None) -> CampaignRedemption:
    red = CampaignRedemption(campaign_id=campaign.id, customer_id=customer_id,
                             order_id=order_id, revenue=money(revenue))
    db.add(red)
    db.flush()
    return red


def metrics(db: Session, *, campaign: Campaign) -> dict:
    status_counts = dict(db.execute(
        select(CampaignMessage.status, func.count()).where(CampaignMessage.campaign_id == campaign.id)
        .group_by(CampaignMessage.status)
    ).all())
    delivered = int(status_counts.get(MessageStatus.DELIVERED.value, 0))
    sent = delivered + int(status_counts.get(MessageStatus.SENT.value, 0))
    failed = int(status_counts.get(MessageStatus.FAILED.value, 0))
    audience = db.scalar(select(func.count()).select_from(CampaignAudience)
                         .where(CampaignAudience.campaign_id == campaign.id)) or 0
    redeemed, revenue = db.execute(
        select(func.count(func.distinct(CampaignRedemption.customer_id)),
               func.coalesce(func.sum(CampaignRedemption.revenue), 0))
        .where(CampaignRedemption.campaign_id == campaign.id)
    ).one()
    redeemed = int(redeemed)
    revenue = round(float(revenue), 2)
    cost = round(delivered * MSG_COST, 2)
    return {
        "audience": int(audience),
        "sent": sent,
        "delivered": delivered,
        "failed": failed,
        "redeemed": redeemed,
        "revenue_generated": revenue,
        "conversion_rate": round(redeemed / delivered, 4) if delivered else 0.0,
        "cost": cost,
        "roi": round((revenue - cost) / cost, 2) if cost > 0 else 0.0,
    }
