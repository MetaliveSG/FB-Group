"""Configurable loyalty & rewards engine.

Reward logic is driven by `RewardRule` rows (config in JSON) — never hardcoded.
Supports: earn-on-spend, first-visit, birthday, repeat-visit, campaign multipliers,
tiers, redemptions, merchant-isolated *and* coalition rewards.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.core.money import money
from app.db.base import utcnow
from app.models.enums import LoyaltyTier, RewardRuleType, RewardScope, RewardTxnType
from app.models.identity import Customer
from app.models.loyalty import (
    Coalition,
    LoyaltyAccount,
    RewardRedemption,
    RewardRule,
    RewardTransaction,
    coalition_members,
)

logger = get_logger("app.loyalty")

# Default tier thresholds by lifetime points (merchant override = PoC limitation).
TIER_THRESHOLDS: list[tuple[int, LoyaltyTier]] = [
    (5000, LoyaltyTier.PLATINUM),
    (2000, LoyaltyTier.GOLD),
    (500, LoyaltyTier.SILVER),
    (0, LoyaltyTier.BRONZE),
]


def tier_for(lifetime_points: int) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if lifetime_points >= threshold:
            return tier.value
    return LoyaltyTier.BRONZE.value


@dataclass
class EarnBreakdown:
    base: int = 0
    first_visit: int = 0
    birthday: int = 0
    repeat_visit: int = 0
    multiplier: float = 1.0
    lines: list[tuple[str, int, str]] = field(default_factory=list)  # (rule_code, points, reason)

    @property
    def total(self) -> int:
        subtotal = self.base + self.first_visit + self.birthday + self.repeat_visit
        return int(round(subtotal * self.multiplier))


def get_or_create_account(db: Session, *, customer_id: str, scope_type: str, scope_id: str,
                          for_update: bool = False) -> LoyaltyAccount:
    """Fetch (or create) a loyalty account. `for_update=True` row-locks it so a
    concurrent spend (wheel/jackpot/redeem) can't double-spend the balance —
    `SELECT ... FOR UPDATE` on Postgres; a harmless no-op on SQLite (tests)."""
    stmt = select(LoyaltyAccount).where(
        LoyaltyAccount.customer_id == customer_id,
        LoyaltyAccount.scope_type == scope_type,
        LoyaltyAccount.scope_id == scope_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    acct = db.scalar(stmt)
    if not acct:
        acct = LoyaltyAccount(customer_id=customer_id, scope_type=scope_type, scope_id=scope_id)
        db.add(acct)
        db.flush()
    return acct


def _active_rules(db: Session, scope_type: str, scope_id: str, now: datetime) -> list[RewardRule]:
    rules = db.scalars(
        select(RewardRule).where(
            RewardRule.scope_type == scope_type,
            RewardRule.scope_id == scope_id,
            RewardRule.is_active.is_(True),
        )
    ).all()
    out = []
    for r in rules:
        if r.valid_from and now < r.valid_from:
            continue
        if r.valid_to and now > r.valid_to:
            continue
        out.append(r)
    return out


def _compute_earn(
    rules: list[RewardRule],
    *,
    amount: Decimal,
    is_first_visit: bool,
    next_visit_count: int,
    customer: Customer | None,
    now: datetime,
) -> EarnBreakdown:
    bd = EarnBreakdown()
    for r in rules:
        cfg = r.config or {}
        if r.rule_type == RewardRuleType.EARN_RATE.value:
            ppd = float(cfg.get("points_per_dollar", 1))
            pts = int(float(amount) * ppd)
            bd.base += pts
            bd.lines.append((r.code, pts, f"Earned {pts} pts on ${amount}"))
        elif r.rule_type == RewardRuleType.FIRST_VISIT.value and is_first_visit:
            bonus = int(cfg.get("bonus", 0))
            bd.first_visit += bonus
            bd.lines.append((r.code, bonus, "First visit bonus"))
        elif r.rule_type == RewardRuleType.BIRTHDAY.value and customer and customer.birthday:
            if customer.birthday.month == now.month:
                bonus = int(cfg.get("bonus", 0))
                bd.birthday += bonus
                bd.lines.append((r.code, bonus, "Birthday month bonus"))
        elif r.rule_type == RewardRuleType.REPEAT_VISIT.value:
            every = int(cfg.get("every", 0)) or 0
            if every and next_visit_count % every == 0:
                bonus = int(cfg.get("bonus", 0))
                bd.repeat_visit += bonus
                bd.lines.append((r.code, bonus, f"Every-{every}-visits bonus"))
        elif r.rule_type == RewardRuleType.CAMPAIGN_MULTIPLIER.value:
            bd.multiplier *= float(cfg.get("multiplier", 1.0))
    return bd


def accrue_for_scope(
    db: Session,
    *,
    customer: Customer,
    scope_type: str,
    scope_id: str,
    amount: Decimal,
    order_id: str | None,
    now: datetime | None = None,
) -> int:
    """Apply all active rules for one scope (merchant or coalition); returns points earned."""
    now = now or utcnow()
    acct = get_or_create_account(db, customer_id=customer.id, scope_type=scope_type, scope_id=scope_id)
    is_first = acct.visit_count == 0
    next_count = acct.visit_count + 1
    rules = _active_rules(db, scope_type, scope_id, now)
    bd = _compute_earn(
        rules, amount=amount, is_first_visit=is_first, next_visit_count=next_count,
        customer=customer, now=now,
    )

    # Ledger entries (one per contributing rule line, multiplier applied proportionally).
    earned = bd.total
    for code, pts, reason in bd.lines:
        scaled = int(round(pts * bd.multiplier))
        if scaled == 0:
            continue
        db.add(RewardTransaction(
            account_id=acct.id, order_id=order_id, txn_type=RewardTxnType.EARN.value,
            points=scaled, reason=reason, rule_code=code,
        ))

    acct.points_balance += earned
    acct.lifetime_points += earned
    acct.visit_count = next_count
    acct.total_spend = money(acct.total_spend + amount)
    acct.last_visit_at = now
    if acct.first_visit_at is None:
        acct.first_visit_at = now
    acct.tier = tier_for(acct.lifetime_points)
    db.flush()
    return earned


def accrue_on_transaction(
    db: Session,
    *,
    customer: Customer,
    merchant_id: str,
    amount: Decimal,
    order_id: str | None,
    now: datetime | None = None,
) -> int:
    """Earn merchant points + any coalition points the merchant participates in."""
    now = now or utcnow()
    merchant_points = accrue_for_scope(
        db, customer=customer, scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id,
        amount=amount, order_id=order_id, now=now,
    )
    # Coalition accrual (separate, configurable program).
    coalition_ids = db.scalars(
        select(coalition_members.c.coalition_id).where(coalition_members.c.merchant_id == merchant_id)
    ).all()
    for cid in coalition_ids:
        coalition = db.get(Coalition, cid)
        if coalition and coalition.is_active:
            accrue_for_scope(
                db, customer=customer, scope_type=RewardScope.COALITION.value, scope_id=cid,
                amount=amount, order_id=order_id, now=now,
            )
    logger.info("loyalty_accrued", extra={"extra": {
        "customer_id": customer.id, "merchant_id": merchant_id,
        "amount": float(amount), "coins_earned": merchant_points, "order_id": order_id}})
    return merchant_points


def redeem(
    db: Session,
    *,
    account: LoyaltyAccount,
    reward_name: str,
    points: int,
    order_id: str | None = None,
) -> RewardRedemption:
    if points <= 0:
        raise ConflictError("Redemption points must be positive", code="bad_redemption")
    if account.points_balance < points:
        raise ConflictError("Insufficient points", code="insufficient_points")
    account.points_balance -= points
    db.add(RewardTransaction(
        account_id=account.id, order_id=order_id, txn_type=RewardTxnType.REDEEM.value,
        points=-points, reason=f"Redeemed: {reward_name}",
    ))
    redemption = RewardRedemption(
        account_id=account.id, order_id=order_id, reward_name=reward_name, points_spent=points,
    )
    db.add(redemption)
    db.flush()
    return redemption
