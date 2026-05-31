"""Merchant-facing loyalty-program config — read/update the standing earn rules.

The base loyalty rules (earn rate, welcome/first-visit bonus, birthday bonus) are
`RewardRule` rows scoped to the merchant. This is the self-serve surface that was missing
(rules were seed/operator-only — the gap that left Bedok Food Hall earning 0 coins).

Keyed by **rule_type**, not code: seed paths use different codes for the earn rule
(`earn` vs `base-earn`), so resolving by type avoids creating duplicates. Time-bound
`CAMPAIGN_MULTIPLIER` promos are NOT managed here — those belong under Campaigns.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RewardRuleType, RewardScope
from app.models.loyalty import RewardRule


def _rule_by_type(db: Session, merchant_id: str, rule_type: RewardRuleType) -> RewardRule | None:
    return db.scalars(
        select(RewardRule)
        .where(
            RewardRule.scope_type == RewardScope.MERCHANT.value,
            RewardRule.scope_id == merchant_id,
            RewardRule.rule_type == rule_type.value,
        )
        .order_by(RewardRule.created_at)
        .limit(1)
    ).first()


def _val(rule: RewardRule | None, key: str) -> float:
    if not rule or not rule.is_active:
        return 0
    return float((rule.config or {}).get(key, 0) or 0)


def get_program(db: Session, *, merchant_id: str) -> dict:
    """Current standing loyalty rules for a merchant. Inactive/absent rule → 0."""
    return {
        "points_per_dollar": _val(_rule_by_type(db, merchant_id, RewardRuleType.EARN_RATE), "points_per_dollar"),
        "welcome_bonus": int(_val(_rule_by_type(db, merchant_id, RewardRuleType.FIRST_VISIT), "bonus")),
        "birthday_bonus": int(_val(_rule_by_type(db, merchant_id, RewardRuleType.BIRTHDAY), "bonus")),
    }


def _upsert(db: Session, merchant_id: str, rule_type: RewardRuleType, default_code: str,
            config: dict, active: bool) -> None:
    rule = _rule_by_type(db, merchant_id, rule_type)
    if rule is None:
        rule = RewardRule(scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id,
                          code=default_code, rule_type=rule_type.value)
        db.add(rule)
    rule.config = config
    rule.is_active = active  # a 0 value deactivates the rule (engine then skips it)


def update_program(db: Session, *, merchant_id: str, points_per_dollar: float,
                   welcome_bonus: int, birthday_bonus: int) -> dict:
    """Idempotently set the three standing rules (upsert by type). A 0 value disables that rule."""
    _upsert(db, merchant_id, RewardRuleType.EARN_RATE, "earn",
            {"points_per_dollar": float(points_per_dollar)}, points_per_dollar > 0)
    _upsert(db, merchant_id, RewardRuleType.FIRST_VISIT, "welcome",
            {"bonus": int(welcome_bonus)}, welcome_bonus > 0)
    _upsert(db, merchant_id, RewardRuleType.BIRTHDAY, "birthday",
            {"bonus": int(birthday_bonus)}, birthday_bonus > 0)
    db.flush()
    return get_program(db, merchant_id=merchant_id)
