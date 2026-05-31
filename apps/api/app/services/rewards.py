"""Customer-facing rewards: loyalty summary, catalog redemption, spin-the-wheel."""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.loyalty.engine import TIER_THRESHOLDS, get_or_create_account, record_reward_txn
from app.models.engagement import RewardCatalogItem, WheelSegment
from app.models.enums import RewardTxnType, RewardScope, WheelPrizeKind
from app.models.identity import Customer
from app.models.loyalty import LoyaltyAccount, RewardRedemption, RewardTransaction
from app.models.orders import Order
from app.models.tenancy import Merchant, Outlet

# Default wheel spin cost (coins). A merchant can override it via
# merchants.settings["wheel_spin_cost"] — see wheel_spin_cost().
WHEEL_SPIN_COST = 10
WHEEL_SPIN_COST_KEY = "wheel_spin_cost"

logger = get_logger("app.rewards")


def wheel_spin_cost(merchant: Merchant | None) -> int:
    """Per-merchant wheel spin cost, falling back to the WHEEL_SPIN_COST default.
    Ignores absent/invalid/negative overrides."""
    if merchant is None:
        return WHEEL_SPIN_COST
    try:
        cost = int((merchant.settings or {}).get(WHEEL_SPIN_COST_KEY))
    except (TypeError, ValueError):
        return WHEEL_SPIN_COST
    return cost if cost >= 0 else WHEEL_SPIN_COST


def _voucher_code() -> str:
    return "VCH-" + secrets.token_hex(4).upper()


def _next_tier(lifetime_points: int) -> tuple[str | None, int]:
    higher = sorted(t for t, _ in TIER_THRESHOLDS if t > lifetime_points)
    if not higher:
        return None, 0
    threshold = higher[0]
    name = next(n.value for t, n in TIER_THRESHOLDS if t == threshold)
    return name, threshold - lifetime_points


def loyalty_summary(db: Session, *, customer_id: str, merchant_id: str) -> dict:
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id)
    next_tier, points_to_next = _next_tier(acct.lifetime_points)
    recent = db.scalars(
        select(RewardTransaction).where(RewardTransaction.account_id == acct.id)
        .order_by(RewardTransaction.created_at.desc()).limit(20)
    ).all()
    return {
        "points_balance": acct.points_balance,
        "lifetime_points": acct.lifetime_points,
        "tier": acct.tier,
        "next_tier": next_tier,
        "points_to_next_tier": points_to_next,
        "visit_count": acct.visit_count,
        "recent": recent,
    }


def my_orders(db: Session, *, customer_id: str, merchant_id: str, limit: int = 20) -> list[dict]:
    """The authenticated customer's order history at this merchant (recent first)."""
    rows = db.scalars(
        select(Order)
        .where(Order.customer_id == customer_id, Order.merchant_id == merchant_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    outlet_ids = {o.outlet_id for o in rows}
    outlet_names = dict(
        db.execute(select(Outlet.id, Outlet.name).where(Outlet.id.in_(outlet_ids))).all()
    ) if outlet_ids else {}
    result = []
    for o in rows:
        items = o.items
        summary = ", ".join(f"{i.quantity}× {i.name_snapshot}" for i in items[:3])
        if len(items) > 3:
            summary += " …"
        result.append({
            "id": o.id,
            "status": o.status,
            "total": float(o.total),
            "items_count": sum(i.quantity for i in items),
            "summary": summary,
            "outlet_name": outlet_names.get(o.outlet_id),
            "created_at": o.created_at,
        })
    return result


def my_profile(db: Session, *, customer: Customer) -> dict:
    return {
        "full_name": customer.full_name,
        "phone": customer.phone,
        "email": customer.email,
        "birthday": customer.birthday,
        "gender": customer.gender,
    }


def update_my_profile(db: Session, *, customer: Customer, phone=None, birthday=None,
                      gender=None, full_name=None) -> dict:
    # Phone is the compulsory identity field. It's stored E.164 (e.g. "+6580000000")
    # so the country code is already carried — multi-region selector is a later add.
    if phone is not None:
        phone = phone.strip()
        if not phone:
            raise ConflictError("Mobile number is required", code="phone_required")
        if phone != customer.phone:
            clash = db.scalars(select(Customer).where(Customer.phone == phone)).first()
            if clash and clash.id != customer.id:
                raise ConflictError("That mobile number is already in use", code="phone_taken")
            customer.phone = phone
    # birthday / gender are optional — an explicit null clears them.
    customer.birthday = birthday
    customer.gender = (gender or None)
    if full_name is not None:
        customer.full_name = full_name
    db.flush()
    return my_profile(db, customer=customer)


def my_vouchers(db: Session, *, customer_id: str, merchant_id: str) -> list[dict]:
    """The customer's reward vouchers at this merchant (active + redeemed, recent first)."""
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id)
    reds = db.scalars(
        select(RewardRedemption).where(RewardRedemption.account_id == acct.id)
        .order_by(RewardRedemption.created_at.desc())
    ).all()
    return [
        {
            "voucher_code": r.voucher_code,
            "reward_name": r.reward_name,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in reds
    ]


def list_catalog(db: Session, *, merchant_id: str, balance: int | None = None) -> list[dict]:
    items = db.scalars(
        select(RewardCatalogItem).where(
            RewardCatalogItem.merchant_id == merchant_id, RewardCatalogItem.is_active.is_(True)
        ).order_by(RewardCatalogItem.sort_order, RewardCatalogItem.cost_points)
    ).all()
    return [
        {
            "id": i.id, "name": i.name, "description": i.description,
            "cost_points": i.cost_points, "kind": i.kind, "value": float(i.value),
            "can_afford": None if balance is None else balance >= i.cost_points,
        }
        for i in items
    ]


def redeem_catalog_item(db: Session, *, customer_id: str, merchant_id: str, item_id: str) -> dict:
    item = db.get(RewardCatalogItem, item_id)
    if not item or item.merchant_id != merchant_id or not item.is_active:
        raise NotFoundError("Reward not found", code="reward_not_found")
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id,
                                 for_update=True)  # row-lock: no concurrent double-redeem
    if acct.points_balance < item.cost_points:
        logger.warning("redeem_insufficient", extra={"extra": {
            "customer_id": customer_id, "merchant_id": merchant_id,
            "item": item.name, "balance": acct.points_balance, "cost": item.cost_points}})
        raise ConflictError("Insufficient points", code="insufficient_points")

    acct.points_balance -= item.cost_points
    record_reward_txn(db, account=acct, txn_type=RewardTxnType.REDEEM.value,
                      points=-item.cost_points, reason=f"Redeemed: {item.name}")
    code = _voucher_code()
    db.add(RewardRedemption(account_id=acct.id, reward_name=item.name,
                            points_spent=item.cost_points, status="redeemed", voucher_code=code))
    db.flush()
    logger.info("reward_redeemed", extra={"extra": {
        "customer_id": customer_id, "merchant_id": merchant_id, "item": item.name,
        "cost": item.cost_points, "voucher": code, "balance": acct.points_balance}})
    return {"voucher_code": code, "reward_name": item.name, "points_balance": acct.points_balance}


@dataclass
class _Seg:
    index: int
    segment: WheelSegment


def _ordered_segments(db: Session, merchant_id: str) -> list[WheelSegment]:
    return list(db.scalars(
        select(WheelSegment).where(WheelSegment.merchant_id == merchant_id)
        .order_by(WheelSegment.sort_order)
    ).all())


def wheel_config(db: Session, *, merchant_id: str) -> dict:
    segs = _ordered_segments(db, merchant_id)
    cost = wheel_spin_cost(db.get(Merchant, merchant_id))
    return {
        "spin_cost": cost,
        "segments": [{"label": s.label, "color": s.color} for s in segs],
    }


def spin_wheel(db: Session, *, customer_id: str, merchant_id: str) -> dict:
    segs = _ordered_segments(db, merchant_id)
    if not segs:
        raise NotFoundError("No wheel configured", code="no_wheel")
    cost = wheel_spin_cost(db.get(Merchant, merchant_id))
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id,
                                 for_update=True)  # row-lock: no concurrent double-spin
    if acct.points_balance < cost:
        logger.warning("wheel_insufficient", extra={"extra": {
            "customer_id": customer_id, "merchant_id": merchant_id,
            "balance": acct.points_balance, "cost": cost}})
        raise ConflictError("Insufficient points to spin", code="insufficient_points")

    # Spend the spin cost.
    acct.points_balance -= cost
    record_reward_txn(db, account=acct, txn_type=RewardTxnType.REDEEM.value,
                      points=-cost, reason="Wheel spin")

    # Weighted random selection.
    total = sum(max(s.weight, 0) for s in segs) or len(segs)
    pick = secrets.randbelow(total)
    cumulative = 0
    chosen_index = 0
    for i, s in enumerate(segs):
        cumulative += max(s.weight, 0)
        if pick < cumulative:
            chosen_index = i
            break
    seg = segs[chosen_index]

    prize = {"kind": seg.prize_kind, "label": seg.label, "points": 0, "voucher_code": None}
    if seg.prize_kind == WheelPrizeKind.POINTS.value and seg.prize_value > 0:
        acct.points_balance += seg.prize_value
        acct.lifetime_points += seg.prize_value
        record_reward_txn(db, account=acct, txn_type=RewardTxnType.EARN.value,
                          points=seg.prize_value, reason=f"Wheel prize: {seg.label}")
        prize["points"] = seg.prize_value
    elif seg.prize_kind == WheelPrizeKind.VOUCHER.value:
        code = _voucher_code()
        db.add(RewardRedemption(account_id=acct.id, reward_name=seg.voucher_name or seg.label,
                                points_spent=0, status="redeemed", voucher_code=code))
        prize["voucher_code"] = code

    db.flush()
    logger.info("wheel_spin", extra={"extra": {
        "customer_id": customer_id, "merchant_id": merchant_id, "index": chosen_index,
        "prize": prize["label"], "kind": prize["kind"], "balance": acct.points_balance}})
    return {
        "winning_index": chosen_index,
        "prize": prize,
        "points_balance": acct.points_balance,
        "spin_cost": cost,
    }
