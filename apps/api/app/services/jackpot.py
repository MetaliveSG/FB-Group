"""3x3 jackpot game — customer-facing, server-authoritative.

How a play works:
1. Spend the spin cost from the customer's merchant loyalty account.
2. Pick the **outcome** server-side via weighted random: a synthetic "lose"
   bucket vs each configured prize (weights are relative). The lose bucket
   weight = sum(prize weights) × LOSE_WEIGHT_MULTIPLIER, which tunes the win
   rate (with `MULTIPLIER=3` → ~25% win rate).
3. Render a 3x3 grid that *matches* the outcome — middle row (the payline)
   gets the won item three times on a win, or a random non-3-match on a loss.
   Top/bottom rows are visual flair only.
4. On a win, mint a `RewardRedemption` row with a voucher code the customer
   can present (the existing voucher pipeline).

The client only animates the grid the server returned — outcomes can't be
gamed in the browser.
"""
from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.base import utcnow
from app.loyalty.engine import get_or_create_account, record_reward_txn
from app.models.engagement import JackpotPrize
from app.models.enums import RewardScope, RewardTxnType
from app.models.loyalty import RewardRedemption
from app.models.tenancy import Merchant

logger = get_logger("app.jackpot")

# Default jackpot spin cost (coins): 0 = free; >0 charges + gates on balance.
# A merchant can override it via merchants.settings["jackpot_spin_cost"] — see
# jackpot_spin_cost().
JACKPOT_SPIN_COST = 5
JACKPOT_SPIN_COST_KEY = "jackpot_spin_cost"
GRID_SIZE = 3
LOSE_WEIGHT_MULTIPLIER = 3  # lose-bucket = total prize weight × this → ~25% win rate

# Progressive "grand jackpot" pot — a real, persistent value (per merchant) that
# grows slowly with elapsed time and resets to BASE when a jackpot is won. The
# pot = BASE + floor(seconds_since_last_reset × RATE), stored as a timestamp in
# merchants.settings so it survives restarts and is shared across all diners.
GRAND_JACKPOT_BASE = 1000
GRAND_JACKPOT_RATE = 0.5  # coins per second (~30/min — slow, persistent)
_GRAND_KEY = "grand_jackpot_since"


def _grand_prize(db: Session, merchant: Merchant | None) -> int:
    """Read-only: pot = base + elapsed×rate. Returns base if not yet anchored
    (the anchor is set at jackpot-seed time / on win — never written during a read)."""
    if merchant is None:
        return GRAND_JACKPOT_BASE
    since = (merchant.settings or {}).get(_GRAND_KEY)
    if not since:
        return GRAND_JACKPOT_BASE
    try:
        since_dt = datetime.fromisoformat(since)
    except (TypeError, ValueError):
        return GRAND_JACKPOT_BASE
    elapsed = (utcnow() - since_dt).total_seconds()
    return GRAND_JACKPOT_BASE + int(max(0.0, elapsed) * GRAND_JACKPOT_RATE)


def _reset_grand_prize(merchant: Merchant) -> None:
    merchant.settings = {**(merchant.settings or {}), _GRAND_KEY: utcnow().isoformat()}


def ensure_grand_anchor(merchant: Merchant) -> bool:
    """Anchor the progressive pot at seed time if it isn't yet (caller commits).
    Returns True if it set the anchor. Idempotent."""
    if not (merchant.settings or {}).get(_GRAND_KEY):
        _reset_grand_prize(merchant)
        return True
    return False


def jackpot_spin_cost(merchant: Merchant | None) -> int:
    """Per-merchant jackpot spin cost, falling back to the JACKPOT_SPIN_COST default.
    Ignores absent/invalid/negative overrides."""
    if merchant is None:
        return JACKPOT_SPIN_COST
    try:
        cost = int((merchant.settings or {}).get(JACKPOT_SPIN_COST_KEY))
    except (TypeError, ValueError):
        return JACKPOT_SPIN_COST
    return cost if cost >= 0 else JACKPOT_SPIN_COST


def _voucher_code() -> str:
    return "JACKPOT-" + secrets.token_hex(4).upper()


def _ordered_prizes(db: Session, merchant_id: str) -> list[JackpotPrize]:
    return list(db.scalars(
        select(JackpotPrize)
        .where(JackpotPrize.merchant_id == merchant_id)
        .order_by(JackpotPrize.sort_order)
    ).all())


def _cell(p: JackpotPrize) -> dict:
    return {"item_name": p.item_name, "item_price": float(p.item_price), "emoji": p.emoji}


def _random_prize(prizes: list[JackpotPrize]) -> JackpotPrize:
    return prizes[secrets.randbelow(len(prizes))]


def _build_grid(prizes: list[JackpotPrize], won: JackpotPrize | None) -> list[list[dict]]:
    """Compose the 3x3 grid. Middle row must reflect the predetermined outcome."""
    if won is not None:
        middle = [won, won, won]
    else:
        # Lose outcome: guarantee the middle row is NOT 3 of the same.
        while True:
            middle = [_random_prize(prizes) for _ in range(GRID_SIZE)]
            if not (middle[0].item_name == middle[1].item_name == middle[2].item_name):
                break
    top = [_random_prize(prizes) for _ in range(GRID_SIZE)]
    bottom = [_random_prize(prizes) for _ in range(GRID_SIZE)]
    return [[_cell(p) for p in row] for row in (top, middle, bottom)]


def jackpot_config(db: Session, *, merchant_id: str) -> dict:
    prizes = _ordered_prizes(db, merchant_id)
    merchant = db.get(Merchant, merchant_id)
    return {
        "spin_cost": jackpot_spin_cost(merchant),
        "grid_size": GRID_SIZE,
        "payline": "middle_row",
        "grand_prize": _grand_prize(db, merchant),
        "prizes": [
            {"item_name": p.item_name, "item_price": float(p.item_price),
             "emoji": p.emoji, "weight": p.weight}
            for p in prizes
        ],
    }


def play_jackpot(db: Session, *, customer_id: str, merchant_id: str) -> dict:
    prizes = _ordered_prizes(db, merchant_id)
    if not prizes:
        raise NotFoundError("No jackpot configured", code="no_jackpot")

    merchant = db.get(Merchant, merchant_id)
    spin_cost = jackpot_spin_cost(merchant)
    acct = get_or_create_account(
        db, customer_id=customer_id,
        scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id,
        for_update=True,  # row-lock: no concurrent double-spin double-charge
    )
    # 1. Charge the spin — only when a cost is configured. With a 0 spin cost the
    #    jackpot is free to play (no food purchase / earned points required), so we
    #    neither gate on balance nor write a redeem ledger row.
    if spin_cost > 0:
        if acct.points_balance < spin_cost:
            logger.warning("jackpot_insufficient", extra={"extra": {
                "customer_id": customer_id, "merchant_id": merchant_id,
                "balance": acct.points_balance, "cost": spin_cost}})
            raise ConflictError("Insufficient points to play", code="insufficient_points")
        acct.points_balance -= spin_cost
        record_reward_txn(db, account=acct, txn_type=RewardTxnType.REDEEM.value,
                          points=-spin_cost, reason="Jackpot spin")

    # 2. Weighted outcome (lose vs win-which-item) — server is authoritative.
    item_weights_total = sum(max(p.weight, 0) for p in prizes) or len(prizes)
    lose_weight = item_weights_total * LOSE_WEIGHT_MULTIPLIER
    pick = secrets.randbelow(item_weights_total + lose_weight)

    won_prize: JackpotPrize | None = None
    if pick < item_weights_total:
        cumulative = 0
        for p in prizes:
            cumulative += max(p.weight, 0)
            if pick < cumulative:
                won_prize = p
                break

    # 3. Render the grid that matches the outcome.
    grid = _build_grid(prizes, won_prize)

    # 4. On a win, mint a voucher AND reset the progressive grand-jackpot pot.
    voucher_code: str | None = None
    if won_prize is not None:
        voucher_code = _voucher_code()
        db.add(RewardRedemption(
            account_id=acct.id,
            reward_name=f"Free {won_prize.item_name}",
            points_spent=0,
            status="active",
            voucher_code=voucher_code,
        ))
        if merchant is not None:
            _reset_grand_prize(merchant)
        logger.info("jackpot_win", extra={"extra": {
            "customer_id": customer_id, "merchant_id": merchant_id,
            "prize": won_prize.item_name, "voucher": voucher_code,
            "grand_prize_reset_to": GRAND_JACKPOT_BASE}})

    db.flush()
    logger.info("jackpot_play", extra={"extra": {
        "customer_id": customer_id, "merchant_id": merchant_id,
        "won": won_prize is not None, "cost": spin_cost,
        "balance": acct.points_balance}})
    return {
        "spin_cost": spin_cost,
        "grid": grid,
        "won": won_prize is not None,
        "prize": (
            {
                "item_name": won_prize.item_name,
                "item_price": float(won_prize.item_price),
                "emoji": won_prize.emoji,
                "voucher_code": voucher_code,
            }
            if won_prize is not None else None
        ),
        "points_balance": acct.points_balance,
    }
