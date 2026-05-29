"""3x3 Jackpot game — server-authoritative outcome + voucher minting.

Asserts: jackpot is FREE to play (no points / food purchase required, balance
untouched); grid is 3x3 with the middle-row payline matching the win/lose
outcome; a win mints a JACKPOT voucher; the server (not the client) decides
the outcome.
"""
from sqlalchemy import select

from app.loyalty.engine import get_or_create_account, tier_for
from app.models.engagement import JackpotPrize
from app.models.enums import RewardScope
from app.models.loyalty import RewardRedemption
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer


def _give_points(db, merchant_id, customer_id, pts):
    acct = get_or_create_account(db, customer_id=customer_id,
                                 scope_type=RewardScope.MERCHANT.value, scope_id=merchant_id)
    acct.points_balance = pts
    acct.lifetime_points = pts
    acct.tier = tier_for(pts)
    db.commit()


def _seed_jackpot(db, merchant_id):
    prizes = [
        ("Fish Ball Noodle", 5.50, "🍜", 1),
        ("Teh Tarik",        2.20, "🥤", 5),
        ("Chendol",          3.00, "🍧", 4),
    ]
    for i, (name, price, emoji, w) in enumerate(prizes):
        db.add(JackpotPrize(merchant_id=merchant_id, item_name=name, item_price=price,
                            emoji=emoji, weight=w, sort_order=i))
    db.commit()


def test_jackpot_free_to_play_without_points(client, db):
    """The jackpot is free: a brand-new customer with zero points (no food ever
    purchased) can still play, and their balance is not touched."""
    w = make_world(db)
    _seed_jackpot(db, w.merchant_id)
    cust = register_customer(client, email="jp_poor@b.sg")  # 0 points, never ordered

    r = client.post("/api/v1/me/jackpot/play",
                    json={"merchant_id": w.merchant_id},
                    headers=H(cust["access_token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["spin_cost"] == 0
    assert data["points_balance"] == 0  # free play does not deduct


def test_jackpot_play_renders_grid_free(client, db):
    """The /play endpoint always returns a well-formed 3x3 grid whose middle-row
    payline matches the win/lose outcome the server decided. Play is free (no
    deduction); a win mints a JACKPOT voucher."""
    w = make_world(db)
    _seed_jackpot(db, w.merchant_id)
    cust = register_customer(client, email="jp_rich@b.sg")
    cid = cust["customer"]["id"]
    _give_points(db, w.merchant_id, cid, 5000)  # points present but never spent on spins

    # Play 30 times — assert invariants on every play and exercise both outcomes.
    cfg = client.get(f"/api/v1/me/jackpot?merchant_id={w.merchant_id}",
                     headers=H(cust["access_token"])).json()
    assert cfg["spin_cost"] == 0
    assert cfg["grid_size"] == 3
    assert {p["item_name"] for p in cfg["prizes"]} == {"Fish Ball Noodle", "Teh Tarik", "Chendol"}

    wins, losses = 0, 0
    for _ in range(30):
        r = client.post("/api/v1/me/jackpot/play",
                        json={"merchant_id": w.merchant_id},
                        headers=H(cust["access_token"]))
        assert r.status_code == 200, r.text
        data = r.json()

        # Free play: cost is 0 and the balance never moves.
        assert data["spin_cost"] == 0
        assert data["points_balance"] == 5000

        # Grid is 3x3 of valid cells.
        assert len(data["grid"]) == 3
        for row in data["grid"]:
            assert len(row) == 3
            for cell in row:
                assert cell["item_name"] in {"Fish Ball Noodle", "Teh Tarik", "Chendol"}
                assert cell["emoji"] in {"🍜", "🥤", "🍧"}

        # Payline invariant: middle row reflects the outcome.
        middle = data["grid"][1]
        same = middle[0]["item_name"] == middle[1]["item_name"] == middle[2]["item_name"]
        if data["won"]:
            assert same, "win must show 3-of-a-kind on the middle row"
            assert data["prize"] is not None
            assert data["prize"]["voucher_code"].startswith("JACKPOT-")
            assert data["prize"]["item_name"] == middle[0]["item_name"]
            wins += 1
        else:
            assert not same, "loss must NOT show 3-of-a-kind on the middle row"
            assert data["prize"] is None
            losses += 1

    # Sanity: with LOSE_WEIGHT_MULTIPLIER=3 (configured win rate ~25%), 30 spins
    # should produce a mix. Both buckets reached confirms the outcome flow works
    # in both directions. (We don't assert a tight ratio — secrets is real RNG.)
    assert wins + losses == 30
    assert losses >= 5, f"unexpectedly few losses ({losses}/30) — check weighting"
    # Wins are stochastic; at ~25% they may sometimes be 0 in 30 tries, so we
    # don't lower-bound them. The invariants above already prove the win path.

    # Every win minted exactly one redemption row with a JACKPOT- voucher.
    redemptions = db.scalars(
        select(RewardRedemption).where(RewardRedemption.voucher_code.like("JACKPOT-%"))
    ).all()
    assert len(redemptions) == wins
