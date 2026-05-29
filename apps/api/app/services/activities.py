"""Activity logging — logged interactions (call/email/meeting/whatsapp/note)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.engagement import CustomerActivity
from app.models.enums import ActivityType


def log_activity(
    db: Session, *, merchant_id: str, customer_id: str, activity_type: str,
    subject: str, body: str = "", occurred_at: datetime | None = None,
    logged_by_user_id: str | None = None,
) -> CustomerActivity:
    act = CustomerActivity(
        merchant_id=merchant_id, customer_id=customer_id,
        activity_type=activity_type or ActivityType.NOTE.value,
        subject=subject, body=body, occurred_at=occurred_at or utcnow(),
        logged_by_user_id=logged_by_user_id,
    )
    db.add(act)
    db.flush()
    return act


def list_for_customer(db: Session, *, merchant_id: str, customer_id: str) -> list[CustomerActivity]:
    return list(db.scalars(
        select(CustomerActivity).where(
            CustomerActivity.merchant_id == merchant_id,
            CustomerActivity.customer_id == customer_id,
        ).order_by(CustomerActivity.occurred_at.desc())
    ).all())
