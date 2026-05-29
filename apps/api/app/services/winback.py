"""Win-back launcher — the RFM → pipeline → campaign retention loop.

Target lapsing/high-value customers (by explicit ids or by RFM segment), open a
win-back opportunity for each, and optionally fire a win-back WhatsApp campaign.
This is the actionable Luckin-style re-activation play.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.rfm import compute_rfm
from app.core.errors import ConflictError
from app.models.campaigns import CampaignAudience
from app.models.enums import RewardScope
from app.models.identity import Customer
from app.models.loyalty import LoyaltyAccount
from app.services import campaigns as campaign_service
from app.services import opportunities as opp_service

DEFAULT_RFM_SEGMENTS = ["At Risk", "Can't Lose Them", "Hibernating"]


def launch(
    db: Session, *, merchant_id: str, owner_user_id: str | None,
    customer_ids: list[str] | None = None, rfm_segments: list[str] | None = None,
    create_campaign: bool = False, message_template: str | None = None,
) -> dict:
    # Tenant isolation comes from merchant_id (targets must hold a merchant account).
    targets: set[str] = set(customer_ids or [])
    if rfm_segments:
        rfm = compute_rfm(db, merchant_id=merchant_id)
        wanted = set(rfm_segments)
        targets.update(c["customer_id"] for c in rfm["customers"] if c["segment"] in wanted)
    if not targets:
        raise ConflictError("No targets — provide customer_ids or rfm_segments", code="no_targets")

    # Keep only customers belonging to this merchant (have a merchant loyalty account).
    valid: list[tuple[str, LoyaltyAccount]] = []
    for cid in targets:
        acct = db.scalar(select(LoyaltyAccount).where(
            LoyaltyAccount.customer_id == cid,
            LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
            LoyaltyAccount.scope_id == merchant_id))
        if acct:
            valid.append((cid, acct))

    for cid, acct in valid:
        cust = db.get(Customer, cid)
        opp_service.create_opportunity(
            db, merchant_id=merchant_id, customer_id=cid,
            name=f"Win-back: {cust.full_name if cust else cid}",
            amount=float(acct.total_spend or 0), pipeline_type="winback", stage="at_risk",
            owner_user_id=owner_user_id, created_by_user_id=owner_user_id)

    result = {"targets": len(valid), "opportunities_created": len(valid),
              "campaign_id": None, "campaign_delivered": 0}

    if create_campaign and valid:
        camp = campaign_service.create_campaign(
            db, merchant_id=merchant_id, name="Win-back outreach", campaign_type="winback",
            message_template=message_template or "Hi {name}, we miss you — here's a treat to welcome you back! 🎁")
        for cid, _ in valid:
            db.add(CampaignAudience(campaign_id=camp.id, customer_id=cid))
        db.flush()
        send = campaign_service.send_campaign(db, merchant_id=merchant_id, campaign=camp)
        result["campaign_id"] = camp.id
        result["campaign_delivered"] = send["delivered"]

    db.flush()
    return result
