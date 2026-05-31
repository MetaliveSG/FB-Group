"""Point-multiplier promotions — time-bound `CAMPAIGN_MULTIPLIER` reward rules.

A promotion is a `RewardRule(rule_type=CAMPAIGN_MULTIPLIER)` scoped to the merchant, with the
boost in `config.multiplier` and an optional active window in `valid_from`/`valid_to`. The
loyalty engine (`_compute_earn` / `_active_rules`) already applies it: any in-window active
multiplier scales every earn line for that scope. This is the *time-bound promo* surface —
distinct from the standing earn rules in `loyalty_admin` (earn rate / welcome / birthday).
"""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.enums import RewardRuleType, RewardScope
from app.models.loyalty import RewardRule


def _to_out(rule: RewardRule) -> dict:
    return {
        "id": rule.id,
        "label": rule.code,
        "multiplier": float((rule.config or {}).get("multiplier", 1)),
        "starts_on": rule.valid_from.date() if rule.valid_from else None,
        "ends_on": rule.valid_to.date() if rule.valid_to else None,
        "is_active": rule.is_active,
    }


def list_promotions(db: Session, *, merchant_id: str) -> list[dict]:
    rules = db.scalars(
        select(RewardRule)
        .where(
            RewardRule.scope_type == RewardScope.MERCHANT.value,
            RewardRule.scope_id == merchant_id,
            RewardRule.rule_type == RewardRuleType.CAMPAIGN_MULTIPLIER.value,
        )
        .order_by(RewardRule.created_at.desc())
    ).all()
    return [_to_out(r) for r in rules]


def create_promotion(db: Session, *, merchant_id: str, label: str, multiplier: float,
                     starts_on: date | None, ends_on: date | None) -> dict:
    """Create a multiplier promo. Dates map to day boundaries (start 00:00:00 → end 23:59:59),
    matching how the engine's window check (`now` between valid_from/valid_to) reads."""
    valid_from = datetime.combine(starts_on, time.min) if starts_on else None
    valid_to = datetime.combine(ends_on, time.max) if ends_on else None
    rule = RewardRule(
        scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id, code=label[:48],
        rule_type=RewardRuleType.CAMPAIGN_MULTIPLIER.value, config={"multiplier": float(multiplier)},
        is_active=True, valid_from=valid_from, valid_to=valid_to,
    )
    db.add(rule)
    db.flush()
    return _to_out(rule)


def deactivate_promotion(db: Session, *, merchant_id: str, promo_id: str) -> None:
    """Turn a promo off. Tenant-guarded: the rule must belong to this merchant and be a
    multiplier (so this endpoint can't disable a standing earn rule or another tenant's)."""
    rule = db.get(RewardRule, promo_id)
    if (rule is None or rule.scope_id != merchant_id
            or rule.scope_type != RewardScope.MERCHANT.value
            or rule.rule_type != RewardRuleType.CAMPAIGN_MULTIPLIER.value):
        raise NotFoundError("Promotion not found", code="promotion_not_found")
    rule.is_active = False
    db.flush()
