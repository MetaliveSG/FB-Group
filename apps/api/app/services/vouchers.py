"""Voucher core — the shared primitive (docs/architecture-vouchers.md).

Issued by loyalty (earned) OR campaign (granted); redeemed by ONE cashier flow: validate (active, in
window, single-use, per-period cap, min-spend, right tenant) → mark used → apply the $ value to the
order. `reward_redemptions` IS the voucher table; `RewardRedemption.status`: issued → redeemed."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.money import money
from app.db.base import utcnow
from app.models.loyalty import RewardRedemption
from app.models.orders import Order
from app.services.rewards import get_or_create_account

# Status lifecycle.
ISSUED, REDEEMED, EXPIRED, VOID = "issued", "redeemed", "expired", "void"
PERIODS = ("day", "week", "month")


def _code() -> str:
    return "VCH-" + secrets.token_hex(4).upper()


def _period_start(now: datetime, period: str | None) -> datetime | None:
    if period not in PERIODS:
        return None
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        return day
    if period == "week":
        return day - timedelta(days=day.weekday())   # Monday
    return day.replace(day=1)                          # month


def issue_vouchers(db: Session, *, customer_id: str, merchant_id: str, name: str, value,
                   count: int = 1, min_spend=0, valid_until: datetime | None = None,
                   per_period: str | None = None, campaign_id: str | None = None,
                   scope_node_id: str | None = None, points_spent: int = 0) -> list[RewardRedemption]:
    """Mint `count` vouchers onto the customer's merchant loyalty account. Used by loyalty (catalog/
    wheel/jackpot) and campaigns (welcome/promo). `scope_node_id` limits redemption to that node's
    subtree (None = tenant-wide). Returns the created vouchers."""
    from app.models.enums import RewardScope
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id)
    out: list[RewardRedemption] = []
    for _ in range(max(1, count)):
        v = RewardRedemption(
            account_id=acct.id, merchant_id=merchant_id, reward_name=name,
            points_spent=points_spent, status=ISSUED, voucher_code=_code(),
            value=money(value), min_spend=money(min_spend), valid_until=valid_until,
            per_period=per_period if per_period in PERIODS else None, campaign_id=campaign_id,
            scope_node_id=scope_node_id,
        )
        db.add(v)
        out.append(v)
    db.flush()
    return out


def issue_welcome_pack(db: Session, *, customer_id: str, merchant_id: str,
                       now: datetime | None = None) -> list[RewardRedemption]:
    """Campaign issuer: if the merchant configured a welcome voucher pack, mint it for a NEW customer.
    Idempotent per (customer, merchant) — never double-issues on a re-login. Config lives in
    `Merchant.settings["welcome_voucher"]` = {enabled, count, value, per_period, valid_days, name}.
    e.g. 10× $1, one per day. Driven by registration (the "granted on signup" trigger)."""
    from app.models.enums import RewardScope
    from app.models.tenancy import Merchant

    m = db.get(Merchant, merchant_id)
    cfg = (m.settings or {}).get("welcome_voucher") if m and isinstance(m.settings, dict) else None
    if not cfg or not cfg.get("enabled"):
        return []
    campaign_id = f"welcome:{merchant_id}"
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id)
    already = db.scalar(select(RewardRedemption.id).where(
        RewardRedemption.account_id == acct.id, RewardRedemption.campaign_id == campaign_id).limit(1))
    if already:
        return []
    now = now or utcnow()
    valid_days = cfg.get("valid_days")
    valid_until = now + timedelta(days=int(valid_days)) if valid_days else None
    return issue_vouchers(db, customer_id=customer_id, merchant_id=merchant_id,
                          name=cfg.get("name", "Welcome voucher"), value=cfg.get("value", 1),
                          count=int(cfg.get("count", 1)), per_period=cfg.get("per_period"),
                          valid_until=valid_until, campaign_id=campaign_id,
                          scope_node_id=cfg.get("scope_node_id"))


def order_storefront_nodes(db: Session, order: Order) -> set[str]:
    """Storefront node ids selling at the order's outlet (menu.id == node.id)."""
    from app.models.catalog import Menu
    return set(db.scalars(select(Menu.id).where(Menu.outlet_id == order.outlet_id)).all())


def validate_voucher(db: Session, *, code: str, merchant_id: str, order_total=None,
                     redeeming_node_ids: set[str] | None = None,
                     now: datetime | None = None) -> RewardRedemption:
    """Resolve + check a voucher for `merchant_id`; raise on any failure. Does NOT mutate (dry-run).
    `redeeming_node_ids` = the storefront node(s) where redemption is happening (for scope check)."""
    now = now or utcnow()
    v = db.scalar(select(RewardRedemption).where(RewardRedemption.voucher_code == code))
    # Don't leak another tenant's voucher → treat wrong-tenant as not-found.
    if v is None or (v.merchant_id and v.merchant_id != merchant_id):
        raise NotFoundError("Voucher not found", code="voucher_not_found")
    if v.status == REDEEMED:
        raise ConflictError("Voucher already used", code="voucher_used")
    if v.status in (EXPIRED, VOID):
        raise ConflictError("Voucher is no longer valid", code="voucher_void")
    if v.valid_until is not None and v.valid_until < now:
        raise ConflictError("Voucher has expired", code="voucher_expired")
    if order_total is not None and v.min_spend and money(order_total) < v.min_spend:
        raise ConflictError(f"Minimum spend of ${v.min_spend} required", code="voucher_min_spend")
    # Per-period cap: at most ONE redemption per period from the same issuance batch (campaign).
    start = _period_start(now, v.per_period)
    if start is not None and v.campaign_id:
        used = db.scalar(
            select(RewardRedemption.id).where(
                RewardRedemption.account_id == v.account_id,
                RewardRedemption.campaign_id == v.campaign_id,
                RewardRedemption.status == REDEEMED,
                RewardRedemption.redeemed_at >= start,
            ).limit(1)
        )
        if used:
            raise ConflictError(f"Only one voucher may be used per {v.per_period}",
                                code="voucher_period_limit")
    # Scope: the redeeming storefront must sit within the voucher's scope subtree (None = tenant-wide).
    if v.scope_node_id and redeeming_node_ids:
        from app.services import org_tree
        if not any(org_tree.node_in_subtree(db, ancestor_id=v.scope_node_id, node_id=n)
                   for n in redeeming_node_ids):
            raise ConflictError("Voucher is not valid at this store", code="voucher_wrong_store")
    return v


def redeem_voucher(db: Session, *, code: str, merchant_id: str, staff_user_id: str | None = None,
                   order: Order | None = None, now: datetime | None = None) -> RewardRedemption:
    """Cashier redeem: validate → mark used → apply the $ value to `order` (if given)."""
    now = now or utcnow()
    order_total = order.total if order is not None else None
    node_ids = order_storefront_nodes(db, order) if order is not None else None
    v = validate_voucher(db, code=code, merchant_id=merchant_id, order_total=order_total,
                         redeeming_node_ids=node_ids, now=now)

    if order is not None:
        if order.voucher_code:
            raise ConflictError("A voucher is already applied to this order", code="voucher_already_applied")
        pre = money(order.subtotal + order.service_charge + order.tax)
        discount = min(money(v.value), pre)            # never discount below $0
        order.discount_amount = discount
        order.voucher_code = v.voucher_code
        order.total = money(pre - discount)
        v.order_id = order.id

    v.status = REDEEMED
    v.redeemed_at = now
    v.redeemed_by_user_id = staff_user_id
    db.flush()
    return v
