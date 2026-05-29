"""Customer-facing /me/orders + /me/vouchers (Orders & Account tabs).

Asserts a customer sees their own order history and vouchers at a merchant, the
data shape is correct, and one customer can never see another's orders.
"""
from app.loyalty.engine import get_or_create_account
from app.models.engagement import RewardCatalogItem
from app.models.enums import RewardScope
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer, place_order, checkout


def _first_item_id(client, qr_token):
    ctx = client.get(f"/api/v1/qr/{qr_token}").json()
    return ctx["menu"]["categories"][0]["items"][0]["id"]


def test_my_orders_lists_history(client, db):
    w = make_world(db)
    cust = register_customer(client, email="mo1@b.sg", phone="+6590000101")
    tok = cust["access_token"]
    item_id = _first_item_id(client, w.qr_token)
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": item_id, "quantity": 2}])
    checkout(client, tok, order["id"])

    r = client.get(f"/api/v1/me/orders?merchant_id={w.merchant_id}", headers=H(tok))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 1
    row = data[0]
    assert row["items_count"] == 2
    assert row["total"] > 0
    assert row["summary"]  # non-empty human summary
    assert "created_at" in row


def test_my_orders_isolated_per_customer(client, db):
    w = make_world(db)
    a = register_customer(client, email="moa@b.sg", phone="+6590000102")
    b = register_customer(client, email="mob@b.sg", phone="+6590000103")
    item_id = _first_item_id(client, w.qr_token)
    order = place_order(client, a["access_token"], w.qr_token, [{"menu_item_id": item_id, "quantity": 1}])
    checkout(client, a["access_token"], order["id"])

    # B (different customer) sees none of A's orders.
    rb = client.get(f"/api/v1/me/orders?merchant_id={w.merchant_id}", headers=H(b["access_token"]))
    assert rb.status_code == 200 and rb.json() == []
    # A sees their own.
    ra = client.get(f"/api/v1/me/orders?merchant_id={w.merchant_id}", headers=H(a["access_token"]))
    assert len(ra.json()) == 1


def test_get_and_update_profile(client, db):
    w = make_world(db)
    cust = register_customer(client, email="prof@b.sg", phone="+6590000201", full_name="Pat")
    tok = cust["access_token"]

    r = client.get("/api/v1/me/profile", headers=H(tok))
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "+6590000201"

    r2 = client.patch("/api/v1/me/profile",
                      json={"phone": "+6590000299", "birthday": "1990-05-20",
                            "gender": "female", "full_name": "Pat Tan"}, headers=H(tok))
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d["phone"] == "+6590000299"
    assert d["birthday"] == "1990-05-20"
    assert d["gender"] == "female"
    assert d["full_name"] == "Pat Tan"


def test_profile_phone_required_and_unique(client, db):
    w = make_world(db)
    a = register_customer(client, email="pa@b.sg", phone="+6590000202")
    register_customer(client, email="pb@b.sg", phone="+6590000203")

    # blank phone rejected (compulsory) — now caught at validation (422, phone format)
    # or the service's required-check (409); either way it's rejected.
    blank = client.patch("/api/v1/me/profile", json={"phone": "   "}, headers=H(a["access_token"]))
    assert blank.status_code in (409, 422)

    # taking another customer's phone rejected
    taken = client.patch("/api/v1/me/profile", json={"phone": "+6590000203"}, headers=H(a["access_token"]))
    assert taken.status_code == 409


def test_profile_update_rejects_malformed_or_overlong_input(client, db):
    """Security: PATCH /me/profile must validate like registration — bad phone format,
    out-of-range gender, and over-column-length values are rejected with 422 (not stored,
    and not left to 500 on Postgres via VARCHAR overflow)."""
    w = make_world(db)
    cust = register_customer(client, email="sec@b.sg", phone="+6590000301")
    tok = cust["access_token"]

    # phone format (letters / too long) — _PhoneMixin
    assert client.patch("/api/v1/me/profile", json={"phone": "<script>"}, headers=H(tok)).status_code == 422
    assert client.patch("/api/v1/me/profile", json={"phone": "+" + "9" * 30}, headers=H(tok)).status_code == 422
    # gender outside the allowed set (and longer than String(16))
    assert client.patch("/api/v1/me/profile", json={"gender": "x" * 50}, headers=H(tok)).status_code == 422
    assert client.patch("/api/v1/me/profile", json={"gender": "alien"}, headers=H(tok)).status_code == 422
    # full_name longer than String(160)
    assert client.patch("/api/v1/me/profile", json={"full_name": "n" * 200}, headers=H(tok)).status_code == 422
    # the stored profile is unchanged after all the rejected attempts
    assert client.get("/api/v1/me/profile", headers=H(tok)).json()["phone"] == "+6590000301"


def test_my_vouchers_lists_redemptions(client, db):
    w = make_world(db)
    cust = register_customer(client, email="vch@b.sg", phone="+6590000104")
    tok = cust["access_token"]

    acct = get_or_create_account(db, customer_id=cust["customer"]["id"],
                                 scope_type=RewardScope.MERCHANT.value, scope_id=w.merchant_id)
    acct.points_balance = 500
    acct.lifetime_points = 500
    db.add(RewardCatalogItem(merchant_id=w.merchant_id, name="Free Coffee", kind="free_item",
                             value=0, cost_points=100, sort_order=0))
    db.commit()

    cat = client.get(f"/api/v1/me/rewards/catalog?merchant_id={w.merchant_id}", headers=H(tok)).json()
    item = next(c for c in cat if c["name"] == "Free Coffee")
    client.post("/api/v1/me/rewards/redeem",
                json={"merchant_id": w.merchant_id, "item_id": item["id"]}, headers=H(tok))

    r = client.get(f"/api/v1/me/vouchers?merchant_id={w.merchant_id}", headers=H(tok))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 1
    assert data[0]["voucher_code"]
    assert data[0]["reward_name"] == "Free Coffee"
    assert data[0]["status"] in {"active", "redeemed"}  # catalog redeem → "redeemed"
