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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.loyalty.engine import get_or_create_account
from app.models.engagement import JackpotPrize
from app.models.enums import RewardScope, RewardTxnType
from app.models.loyalty import RewardRedemption, RewardTransaction

JACKPOT_SPIN_COST = 0   # points per play; 0 = free to play (no purchase/points needed)
GRID_SIZE = 3
LOSE_WEIGHT_MULTIPLIER = 3  # lose-bucket = total prize weight × this → ~25% win rate


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
    return {
        "spin_cost": JACKPOT_SPIN_COST,
        "grid_size": GRID_SIZE,
        "payline": "middle_row",
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

    acct = get_or_create_account(
        db, customer_id=customer_id,
        scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id,
    )
    # 1. Charge the spin — only when a cost is configured. With JACKPOT_SPIN_COST=0
    #    the jackpot is free to play (no food purchase / earned points required),
    #    so we neither gate on balance nor write a redeem ledger row.
    if JACKPOT_SPIN_COST > 0:
        if acct.points_balance < JACKPOT_SPIN_COST:
            raise ConflictError("Insufficient points to play", code="insufficient_points")
        acct.points_balance -= JACKPOT_SPIN_COST
        db.add(RewardTransaction(
            account_id=acct.id, txn_type=RewardTxnType.REDEEM.value,
            points=-JACKPOT_SPIN_COST, reason="Jackpot spin",
        ))

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

    # 4. On a win, mint a voucher.
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

    db.flush()
    return {
        "spin_cost": JACKPOT_SPIN_COST,
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
